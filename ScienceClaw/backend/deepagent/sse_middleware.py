"""
SSE 监控中间件 — 基于 sample/monitoring_v2.py 的模式。

通过 AgentMiddleware 的 wrap_tool_call 拦截工具执行的前后，
在工具执行层捕获：
  - 工具调用前：工具名称、输入参数、开始时间
  - 工具执行后：返回结果、执行耗时
  - Todolist 变化：对比前后 todolist 的增删改

产生的事件存储在 sse_events 列表中，由 runner.py 在 stream 循环中轮询并 yield。
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from langchain.agents.middleware import AgentMiddleware

from backend.deepagent.sse_protocol import get_protocol_manager


_SKILL_READ_TOOL_NAMES = {"read_file", "sandbox_read_file", "file_read"}
_REVIEW_GATED_TOOL_NAMES = {"obsidian_rewrite_materials_review_note"}
_SKILL_PATH_RE = re.compile(
    r"(?i)(?:^|[\\/])(?:skills|builtin-skills|builtin_skills|Skills)(?:[\\/])([^\\/]+)[\\/]SKILL\.md$"
)


# ───────────────────────────────────────────────────────────────────
# 中间件事件（轻量结构，供 runner 消费）
# ───────────────────────────────────────────────────────────────────

class MiddlewareEvent:
    """中间件生成的事件，最终由 runner 转换为 SSE 事件发送给前端"""

    __slots__ = ("event", "data")

    def __init__(self, event: str, data: Dict[str, Any]):
        self.event = event
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {"event": self.event, "data": self.data}


# ───────────────────────────────────────────────────────────────────
# SSE 监控中间件
# ───────────────────────────────────────────────────────────────────

class SSEMonitoringMiddleware(AgentMiddleware):
    """
    SSE 监控中间件 — 拦截工具执行前后的参数和结果。

    核心机制（参考 monitoring_v2.py 的 wrap_tool_call）：
      1. 工具执行前：提取 tool_name, tool_args，记录 start_time
      2. 调用 handler(request) 执行实际工具
      3. 工具执行后：计算 duration_ms，提取结果
      4. 生成 SSE 事件存入 sse_events 列表
      5. runner 在每个 stream chunk 后轮询 sse_events

    使用方式（参考 scienceclaw_agent_v5.py）：
      middleware = SSEMonitoringMiddleware(agent_name="DeepAgent")
      agent = create_deep_agent(
          model=model,
          tools=tools,
          middleware=[middleware],  # 注入中间件
      )
      # 在 stream 循环中轮询：
      async for chunk in agent.astream(...):
          yield from middleware.drain_events()
    """

    def __init__(
        self,
        agent_name: str = "agent",
        parent_agent: Optional[str] = None,
        verbose: bool = False,
    ):
        super().__init__()
        self.agent_name = agent_name
        self.parent_agent = parent_agent
        self.verbose = verbose

        # 事件队列（runner 轮询消费，线程安全）
        self._events_lock = threading.Lock()
        self.sse_events: List[MiddlewareEvent] = []

        # 日志
        self.execution_log: List[Dict[str, Any]] = []
        self.tool_calls_log: List[Dict[str, Any]] = []
        self.todos_log: List[Dict[str, Any]] = []

        # Todolist 对比用
        self.previous_todos: List[Dict[str, Any]] = []

        # 统计
        self.total_tool_calls: int = 0
        self.total_tool_duration_ms: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0

        # 协议管理器（获取工具元数据）
        self.required_skills: List[str] = []
        self.read_skills: List[str] = []
        self._read_skill_set: set[str] = set()
        self._protocol = get_protocol_manager()

    # ── 路径标识 ──

    def _get_agent_path(self) -> str:
        if self.parent_agent:
            return f"{self.parent_agent} -> {self.agent_name}"
        return self.agent_name

    def _push_event(self, event: str, data: Dict[str, Any]) -> None:
        with self._events_lock:
            self.sse_events.append(MiddlewareEvent(event=event, data=data))

    def set_required_skills(self, skills: List[str]) -> None:
        ordered = [str(skill).strip() for skill in skills if str(skill).strip()]
        deduped: List[str] = []
        seen: set[str] = set()
        for skill in ordered:
            if skill in seen:
                continue
            seen.add(skill)
            deduped.append(skill)
        self.required_skills = deduped
        for skill in self.required_skills:
            self._push_event(
                "middleware_skill_required",
                {
                    "skill_name": skill,
                    "required_skills": list(self.required_skills),
                    "timestamp": time.time(),
                },
            )

    def get_skill_state(self) -> Dict[str, List[str]]:
        missing = [skill for skill in self.required_skills if skill not in self._read_skill_set]
        return {
            "required_skills": list(self.required_skills),
            "read_skills": list(self.read_skills),
            "missing_required_skills": missing,
        }

    def _extract_skill_name(self, tool_name: str, tool_args: Optional[Dict[str, Any]]) -> Optional[str]:
        if tool_name not in _SKILL_READ_TOOL_NAMES or not isinstance(tool_args, dict):
            return None
        for key in ("file", "file_path", "path"):
            raw_path = tool_args.get(key)
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            match = _SKILL_PATH_RE.search(raw_path.strip())
            if match:
                return match.group(1)
        return None

    def _record_skill_read(self, skill_name: str) -> None:
        if not skill_name or skill_name in self._read_skill_set:
            return
        self._read_skill_set.add(skill_name)
        self.read_skills.append(skill_name)
        state = self.get_skill_state()
        self._push_event(
            "middleware_skill_read",
            {
                "skill_name": skill_name,
                **state,
                "timestamp": time.time(),
            },
        )

    def _guard_required_skills(self, tool_name: str, tool_args: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not self.required_skills:
            return None

        should_guard = False
        if tool_name in _REVIEW_GATED_TOOL_NAMES:
            should_guard = True
        elif tool_name == "obsidian_write_materials_note":
            note_type = str((tool_args or {}).get("note_type", "")).strip().lower()
            should_guard = note_type == "review"

        if not should_guard:
            return None

        state = self.get_skill_state()
        if not state["missing_required_skills"]:
            return None

        for skill in state["missing_required_skills"]:
            self._push_event(
                "middleware_skill_missing",
                {
                    "skill_name": skill,
                    **state,
                    "timestamp": time.time(),
                },
            )

        return {
            "ok": False,
            "error": (
                "Required local skills were not read before the review write step: "
                + ", ".join(state["missing_required_skills"])
            ),
            **state,
        }

    # ── 核心：拦截工具调用前后 ──

    def _before_tool(self, request: Any):
        """工具执行前：解析信息、记录开始、生成 start 事件"""
        tool_name, tool_args, tool_call_id = self._extract_tool_info(request)
        start_time = time.time()
        tool_meta = self._protocol.get_tool_meta(tool_name or "unknown")
        skill_name = self._extract_skill_name(tool_name or "", tool_args)
        if skill_name:
            self._record_skill_read(skill_name)

        if tool_name:
            self.total_tool_calls += 1
            with self._events_lock:
                self.sse_events.append(MiddlewareEvent(
                    event="middleware_tool_start",
                    data={
                        "tool_call_id": tool_call_id,
                        "function": tool_name,
                        "args": tool_args or {},
                        "tool_meta": tool_meta,
                        "timestamp": start_time,
                    },
                ))
            self.tool_calls_log.append({
                "agent": self.agent_name,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "tool_call_id": tool_call_id,
                "start_time": start_time,
                "phase": "start",
            })
            if self.verbose:
                logger.info(
                    f"[{self._get_agent_path()}] TOOL START: "
                    f"{tool_meta.get('icon', '🔧')} {tool_name} | "
                    f"args={json.dumps(tool_args or {}, ensure_ascii=False)[:200]}"
                )

        return tool_name, tool_args, tool_call_id, start_time, tool_meta

    def _after_tool(self, result: Any, tool_name, tool_args, tool_call_id, start_time, tool_meta):
        """工具执行后：计算耗时、生成 complete 事件、处理 todolist"""
        duration_ms = int((time.time() - start_time) * 1000)
        self.total_tool_duration_ms += duration_ms
        if isinstance(result, dict) and tool_name and tool_name.startswith("obsidian_"):
            state = self.get_skill_state()
            result.setdefault("required_skills", state["required_skills"])
            result.setdefault("read_skills", state["read_skills"])
            result.setdefault("missing_required_skills", state["missing_required_skills"])

        if tool_name:
            result_summary = self._extract_result_summary(result)
            with self._events_lock:
                self.sse_events.append(MiddlewareEvent(
                    event="middleware_tool_complete",
                    data={
                        "tool_call_id": tool_call_id,
                        "function": tool_name,
                        "duration_ms": duration_ms,
                        "tool_meta": tool_meta,
                        "result_summary": result_summary,
                        "timestamp": time.time(),
                    },
                ))
            self.tool_calls_log.append({
                "agent": self.agent_name,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "duration_ms": duration_ms,
                "phase": "complete",
            })
            if self.verbose:
                logger.info(
                    f"[{self._get_agent_path()}] TOOL COMPLETE: "
                    f"{tool_meta.get('icon', '🔧')} {tool_name} | "
                    f"duration={duration_ms}ms"
                )

        if tool_name == "write_todos":
            self._handle_todos_change(tool_args)

        return result

    def wrap_tool_call(
        self,
        request: Any,
        handler: Callable[[Any], Any],
    ) -> Any:
        """同步版本 — 拦截工具执行前后（供 invoke/stream 调用）"""
        tool_name, tool_args, tool_call_id, start_time, tool_meta = self._before_tool(request)
        guarded_result = self._guard_required_skills(tool_name or "", tool_args)
        result = guarded_result if guarded_result is not None else handler(request)
        return self._after_tool(result, tool_name, tool_args, tool_call_id, start_time, tool_meta)

    async def awrap_tool_call(
        self,
        request: Any,
        handler: Callable,
    ) -> Any:
        """异步版本 — 拦截工具执行前后（供 ainvoke/astream 调用）"""
        tool_name, tool_args, tool_call_id, start_time, tool_meta = self._before_tool(request)
        guarded_result = self._guard_required_skills(tool_name or "", tool_args)
        result = guarded_result if guarded_result is not None else await handler(request)
        return self._after_tool(result, tool_name, tool_args, tool_call_id, start_time, tool_meta)

    # ── 辅助方法 ──

    def _extract_tool_info(self, request: Any) -> tuple:
        """
        从 request 中提取工具信息。

        参考 monitoring_v2.py 的实现，支持两种 request 格式：
          - ToolCallRequest 对象（hasattr(request, 'tool_call')）
          - 字典
        """
        tool_name = None
        tool_args = None
        tool_call_id = ""

        if hasattr(request, 'tool_call'):
            tool_call = request.tool_call
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id", uuid.uuid4().hex)
        elif isinstance(request, dict):
            tool_name = request.get("name")
            tool_args = request.get("args", {})
            tool_call_id = request.get("id", uuid.uuid4().hex)

        return tool_name, tool_args, tool_call_id

    def _extract_result_summary(self, result: Any) -> str:
        """提取工具结果摘要（用于日志，不影响实际返回值）"""
        try:
            if result is None:
                return "(no output)"
            if isinstance(result, str):
                return result[:200] + "..." if len(result) > 200 else result
            if isinstance(result, dict):
                s = json.dumps(result, ensure_ascii=False)
                return s[:200] + "..." if len(s) > 200 else s
            if hasattr(result, 'content'):
                content = result.content
                if isinstance(content, str):
                    return content[:200] + "..." if len(content) > 200 else content
            return str(result)[:200]
        except Exception:
            return "(error extracting result)"

    def _handle_todos_change(self, tool_args: Optional[Dict[str, Any]]):
        """
        处理 write_todos 工具的 todolist 变化（参考 monitoring_v2.py 的 _compare_todos）
        """
        if not isinstance(tool_args, dict) or "todos" not in tool_args:
            return

        new_todos = tool_args["todos"]
        if not isinstance(new_todos, list):
            return

        # 对比前后 todolist
        changes = self._compare_todos(self.previous_todos, new_todos)

        # 记录日志
        entry = {
            "agent": self.agent_name,
            "phase": "todos_update",
            "timestamp": time.time(),
            "todos": new_todos,
            "changes": changes,
        }
        self.todos_log.append(entry)

        with self._events_lock:
            self.sse_events.append(MiddlewareEvent(
                event="middleware_todos_update",
                data={
                    "todos": new_todos,
                    "changes": changes,
                    "agent": self.agent_name,
                    "timestamp": time.time(),
                },
            ))

        if self.verbose:
            self._print_todos_changes(changes, new_todos)

        # 更新存储
        self.previous_todos = [dict(t) for t in new_todos]

    def _compare_todos(
        self,
        old_todos: List[Dict[str, Any]],
        new_todos: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """对比前后两次 todolist 的变化（与 monitoring_v2.py 逻辑一致）"""
        changes: Dict[str, list] = {
            "added": [],
            "removed": [],
            "status_changed": [],
            "unchanged": [],
        }

        old_map = {t.get("content", ""): t for t in old_todos}
        new_map = {t.get("content", ""): t for t in new_todos}

        for content, new_todo in new_map.items():
            if content not in old_map:
                changes["added"].append({
                    "content": content,
                    "status": new_todo.get("status", "unknown"),
                })
            else:
                old_status = old_map[content].get("status", "unknown")
                new_status = new_todo.get("status", "unknown")
                if old_status != new_status:
                    changes["status_changed"].append({
                        "content": content,
                        "old_status": old_status,
                        "new_status": new_status,
                    })
                else:
                    changes["unchanged"].append({
                        "content": content,
                        "status": new_status,
                    })

        for content in old_map:
            if content not in new_map:
                changes["removed"].append({
                    "content": content,
                    "status": old_map[content].get("status", "unknown"),
                })

        return changes

    def _print_todos_changes(self, changes: Dict[str, Any], all_todos: List[Dict[str, Any]]):
        """打印 todolist 变化（与 monitoring_v2.py 一致）"""
        status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅'}
        logger.info(f"[{self._get_agent_path()}] TODOLIST UPDATE:")
        for item in changes.get("added", []):
            emoji = status_emoji.get(item["status"], '')
            logger.info(f"  + {emoji} [{item['status']}] {item['content']}")
        for item in changes.get("status_changed", []):
            old_e = status_emoji.get(item["old_status"], '')
            new_e = status_emoji.get(item["new_status"], '')
            logger.info(f"  {old_e} [{item['old_status']}] → {new_e} [{item['new_status']}] {item['content']}")
        logger.info(f"  Total: {len(all_todos)} todos")

    # ── 事件消费接口（供 runner 调用）──

    def drain_events(self) -> List[Dict[str, Any]]:
        """
        取出所有待处理事件并清空队列。

        runner.py 在每个 stream chunk 后调用此方法，
        与 scienceclaw_agent_v5.py 中的 _yield_new_sse_events() 模式一致。
        """
        with self._events_lock:
            events = [evt.to_dict() for evt in self.sse_events]
            self.sse_events.clear()
        return events

    def clear(self):
        """清空所有状态"""
        with self._events_lock:
            self.sse_events.clear()
        self.execution_log.clear()
        self.tool_calls_log.clear()
        self.todos_log.clear()
        self.previous_todos.clear()
        self.total_tool_calls = 0
        self.total_tool_duration_ms = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.required_skills = []
        self.read_skills = []
        self._read_skill_set.clear()

    def add_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
        """累积 token 使用量"""
        if input_tokens and input_tokens > 0:
            self.input_tokens += input_tokens
        if output_tokens and output_tokens > 0:
            self.output_tokens += output_tokens

    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            "total_tool_calls": self.total_tool_calls,
            "total_tool_duration_ms": self.total_tool_duration_ms,
            "todos_updates": len(self.todos_log),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
        }
