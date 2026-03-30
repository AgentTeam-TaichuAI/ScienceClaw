"""
runner.py — SSE 流式执行器。

职责：从 agent.py 获取构建好的 agent，执行对话并将结果以 SSE 事件格式推送给前端。
agent 的构建（模型、工具、提示词）全部由 agent.py 负责。

架构（参考 sample/scienceclaw_agent_v5.py + sample/monitoring_v2.py）：
  - agent.py 创建 agent 时注入 SSEMonitoringMiddleware
  - 中间件的 wrap_tool_call 拦截工具执行前后，捕获参数/结果/耗时
  - 中间件事件存储在 middleware.sse_events 列表
  - runner 在每个 stream chunk 后调用 middleware.drain_events() 轮询事件
  - 中间件事件与 stream 事件合并，一起 yield 给前端

这样实现了两层事件来源：
  1. 中间件层：精确的工具前后拦截（参数、结果、精准计时、todolist 变化）
  2. Stream 层：AI 回复内容、最终消息（只有 content 需要从 stream 获取）
"""
from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from backend.deepagent.agent import deep_agent, deep_agent_eval
from backend.deepagent.diagnostic import DIAGNOSTIC_ENABLED
from backend.deepagent.plan_types import PlanStep, normalize_plan_steps
from backend.deepagent.sessions import ScienceSession
from backend.deepagent.sse_middleware import SSEMonitoringMiddleware
from backend.task_settings import get_task_settings, TaskSettings


# ───────────────────────────────────────────────────────────────────
# 辅助
# ───────────────────────────────────────────────────────────────────

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_CONTENT_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)
_ZOTERO_OBSIDIAN_REQUIRED_SKILLS = [
    "zotero-materials-review",
    "literature-review",
    "scientific-writing",
    "obsidian-markdown",
    "materials-obsidian",
]
_REVIEW_REWRITE_RE = re.compile(
    r"(改写|改成|继续修改|继续改写|继续润色|润色|学术|科研|论文|GB/T\s*7714|GB7714|cit(e|ation))",
    re.IGNORECASE,
)
_ZOTERO_REVIEW_RE = re.compile(
    r"(zotero|better bibtex|bbt|obsidian|review agent|综述|文献综述|literature review|pdf)",
    re.IGNORECASE,
)


def _infer_required_skills(
    query: str,
    attachments: List[str] | None,
    session: ScienceSession | None,
) -> List[str]:
    lowered_query = (query or "").strip()
    attachment_names = [str(path or "").lower() for path in attachments or []]
    has_json_attachment = any(name.endswith(".json") for name in attachment_names)
    has_recent_review = bool(getattr(session, "latest_review_context", {}) or {}) if session else False
    rewrite_intent = has_recent_review and bool(_REVIEW_REWRITE_RE.search(lowered_query))
    zotero_review_intent = bool(_ZOTERO_REVIEW_RE.search(lowered_query)) or has_json_attachment
    if rewrite_intent or zotero_review_intent:
        return list(_ZOTERO_OBSIDIAN_REQUIRED_SKILLS)
    return []


def _yield_skill_events_from_middleware(middleware: SSEMonitoringMiddleware):
    for mw_evt in middleware.drain_events():
        mw_type = mw_evt.get("event", "")
        mw_data = mw_evt.get("data", {})
        if mw_type == "middleware_skill_required":
            yield {"event": "skill_required", "data": mw_data}
        elif mw_type == "middleware_skill_read":
            yield {"event": "skill_read", "data": mw_data}
        elif mw_type == "middleware_skill_missing":
            yield {"event": "skill_missing", "data": mw_data}


def _extract_thinking(msg: "AIMessage") -> tuple[str, str]:
    """从 AIMessage 中提取思考内容和干净的正文。

    支持三种模型格式：
      1. DeepSeek（OpenAI 兼容 API）: additional_kwargs["reasoning_content"]
      2. Claude: content blocks 中 type="thinking" 的块
      3. DeepSeek / Qwen（原生 API）: <think>...</think> 标签

    Returns:
        (thinking_content, clean_text_content)
    """
    thinking = ""

    # ① additional_kwargs.reasoning_content（DeepSeek via OpenAI API）
    reasoning = (msg.additional_kwargs or {}).get("reasoning_content", "")
    if isinstance(reasoning, str) and reasoning.strip():
        thinking = reasoning.strip()

    content = msg.content
    if not content:
        return thinking, ""

    # ② content 是 list（Claude 风格 content blocks）
    if isinstance(content, list):
        thinking_parts: list[str] = []
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "thinking":
                    thinking_parts.append(block.get("thinking", ""))
                elif btype == "text":
                    text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        if thinking_parts and not thinking:
            thinking = "\n".join(p for p in thinking_parts if p)
        return thinking, "\n".join(text_parts).strip()

    # ③ content 是 str（可能含 <think> 标签）
    if isinstance(content, str):
        if not thinking:
            matches = _THINK_CONTENT_RE.findall(content)
            if matches:
                thinking = "\n".join(m.strip() for m in matches if m.strip())
        clean = _THINK_TAG_RE.sub("", content).strip()
        return thinking, clean

    return thinking, str(content)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1.5 chars per token for mixed CJK/English."""
    if not text:
        return 0
    return max(1, len(text) * 2 // 3)


def _extract_token_usage(msg) -> Dict[str, int]:
    """Extract input/output token counts from a LangChain message.

    Returns dict with 'input_tokens' and 'output_tokens' keys.
    """
    input_tokens = 0
    output_tokens = 0

    # 方式1: usage_metadata (LangChain 标准)
    usage_meta = getattr(msg, "usage_metadata", None)
    if usage_meta:
        input_tokens = usage_meta.get("input_tokens", 0)
        output_tokens = usage_meta.get("output_tokens", 0)
        if input_tokens or output_tokens:
            logger.debug(f"[DeepAgent] Got tokens from usage_metadata: {usage_meta}")
            return {"input_tokens": input_tokens, "output_tokens": output_tokens}

    # 方式2: response_metadata.token_usage (OpenAI 风格)
    resp_meta = getattr(msg, "response_metadata", {}) or {}
    token_usage = resp_meta.get("token_usage", {})
    if token_usage:
        input_tokens = token_usage.get("prompt_tokens", 0)
        output_tokens = token_usage.get("completion_tokens", 0)
        if input_tokens or output_tokens:
            logger.debug(f"[DeepAgent] Got tokens from response_metadata.token_usage: {token_usage}")
            return {"input_tokens": input_tokens, "output_tokens": output_tokens}

    # 方式3: response_metadata.usage (某些 API)
    usage = resp_meta.get("usage", {})
    if usage:
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        if input_tokens or output_tokens:
            logger.debug(f"[DeepAgent] Got tokens from response_metadata.usage: {usage}")
            return {"input_tokens": input_tokens, "output_tokens": output_tokens}

    # 方式4: additional_kwargs.usage (某些 API)
    add_kwargs = getattr(msg, "additional_kwargs", {}) or {}
    usage = add_kwargs.get("usage", {})
    if usage:
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        if input_tokens or output_tokens:
            logger.debug(f"[DeepAgent] Got tokens from additional_kwargs.usage: {usage}")
            return {"input_tokens": input_tokens, "output_tokens": output_tokens}

    return {"input_tokens": 0, "output_tokens": 0}


def _estimate_message_tokens(msg) -> int:
    """Estimate token count for a single LangChain message."""
    tokens = 4  # message overhead
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        tokens += _estimate_tokens(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                tokens += _estimate_tokens(block.get("text", "") or block.get("content", ""))
            elif isinstance(block, str):
                tokens += _estimate_tokens(block)
    if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
        for tc in msg.tool_calls:
            tokens += _estimate_tokens(tc.get("name", ""))
            args = tc.get("args", {})
            tokens += _estimate_tokens(json.dumps(args, ensure_ascii=False, default=str) if isinstance(args, dict) else str(args))
    return tokens


def _truncate_tool_args(args: dict, max_chars: int = 500) -> dict:
    """Truncate large values in tool call args to prevent context bloat."""
    truncated = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > max_chars:
            truncated[k] = v[:max_chars] + f"... ({len(v)} chars total, truncated)"
        else:
            truncated[k] = v
    return truncated


def _compute_history_token_budget(
    context_window: int,
    output_reserve: int = 16384,
    system_prompt_tokens: int = 4000,
    tools_tokens: int = 6000,
    current_query_tokens: int = 1000,
    safety_margin: float = 0.15,
) -> int:
    """Dynamically compute history token budget based on model context window.

    Formula: history_budget = context_window × (1 - safety_margin) - reserved

    output_reserve is separate from max_tokens:
    - max_tokens = output ceiling (how long a reply the model is *allowed* to produce)
    - output_reserve = how much space to *actually set aside* for output in the budget
    For DeepSeek v3.2 (8K actual output), 16K reserve is generous.
    For Opus 4.6 / GPT 5.2 with longer outputs, users can raise this.
    """
    usable = int(context_window * (1 - safety_margin))
    reserved = output_reserve + system_prompt_tokens + tools_tokens + current_query_tokens
    budget = max(usable - reserved, 8000)
    return budget


_ASSISTANT_CONTENT_MAX_LEN = 3000
_TOOL_RESULT_MAX_LEN = 2000
_TOOL_ARGS_MAX_LEN = 500


def _build_history_messages(
    session: "ScienceSession",
    current_query: str = "",
    max_rounds: int = 6,
    max_history_tokens: int = 60000,
) -> List:
    """
    从 session.events 中提取最近 max_rounds 轮对话历史，
    构造完整的 LangChain 消息列表（HumanMessage / AIMessage / ToolMessage）。

    三重保护：
      1. 单条消息截断（assistant 回复、工具参数、工具结果）
      2. 按轮次截取（max_rounds）
      3. 按 token 估算截取（max_history_tokens），从最旧的轮次开始丢弃

    max_history_tokens 应由调用方根据 context_window 动态计算。
    """
    messages: List = []
    pending_tool_calls: List[dict] = []

    def _flush_pending_calls():
        nonlocal pending_tool_calls
        if not pending_tool_calls:
            return
        tool_calls = [
            {
                "id": tc.get("tool_call_id", ""),
                "name": tc.get("function", "unknown"),
                "args": _truncate_tool_args(
                    tc.get("args") if isinstance(tc.get("args"), dict) else {},
                    max_chars=_TOOL_ARGS_MAX_LEN,
                ),
                "type": "tool_call",
            }
            for tc in pending_tool_calls
        ]
        messages.append(AIMessage(content="", tool_calls=tool_calls))
        pending_tool_calls = []

    for evt in session.events:
        event_type = evt.get("event", "")
        data = evt.get("data", {})

        if event_type == "message":
            _flush_pending_calls()
            role = data.get("role", "")
            content = data.get("content", "")
            if not content:
                continue
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, default=str) if isinstance(content, (dict, list)) else str(content)
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                if len(content) > _ASSISTANT_CONTENT_MAX_LEN:
                    content = content[:_ASSISTANT_CONTENT_MAX_LEN] + \
                        f"\n... (response truncated, {len(content)} chars total)"
                messages.append(AIMessage(content=content))

        elif event_type == "tool":
            status = data.get("status", "")

            if status == "calling":
                pending_tool_calls.append(data)

            elif status == "called":
                _flush_pending_calls()

                content = data.get("content", "")
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False)
                elif isinstance(content, list):
                    content = json.dumps(content, ensure_ascii=False, default=str)
                elif not isinstance(content, str):
                    content = str(content)

                if len(content) > _TOOL_RESULT_MAX_LEN:
                    content = content[:_TOOL_RESULT_MAX_LEN] + "\n... (truncated)"

                messages.append(ToolMessage(
                    content=content or "(no output)",
                    tool_call_id=data.get("tool_call_id", ""),
                    name=data.get("function", ""),
                ))

    _flush_pending_calls()

    if current_query and messages and isinstance(messages[-1], HumanMessage):
        if messages[-1].content.strip() == current_query.strip():
            messages.pop()

    # Pass 1: 按轮次截取
    user_indices = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    if len(user_indices) > max_rounds:
        start_idx = user_indices[-max_rounds]
        messages = messages[start_idx:]

    # Pass 2: 按 token 估算截取 — 从最旧的轮次开始丢弃，直到总量在预算内
    total_tokens = sum(_estimate_message_tokens(m) for m in messages)
    if total_tokens > max_history_tokens:
        logger.warning(
            f"[History] Estimated {total_tokens} tokens exceeds budget {max_history_tokens}, "
            f"trimming oldest rounds"
        )
        user_indices = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
        while total_tokens > max_history_tokens and len(user_indices) > 1:
            cut_end = user_indices[1]
            removed = messages[:cut_end]
            removed_tokens = sum(_estimate_message_tokens(m) for m in removed)
            messages = messages[cut_end:]
            total_tokens -= removed_tokens
            user_indices = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
        logger.info(f"[History] Trimmed to {len(messages)} messages, ~{total_tokens} tokens")

    # Pass 3: 确保消息列表不以 ToolMessage 开头（会导致 API 错误）
    while messages and isinstance(messages[0], ToolMessage):
        messages.pop(0)
    while messages and isinstance(messages[0], AIMessage) and not messages[0].content and getattr(messages[0], "tool_calls", None):
        messages.pop(0)
        while messages and isinstance(messages[0], ToolMessage):
            messages.pop(0)

    return messages


def _build_plan(description: str) -> List[PlanStep]:
    """构造一个单步 plan（ReAct agent 无需多步规划）。"""
    return normalize_plan_steps([{
        "id": "S1",
        "content": description,
        "status": "pending",
        "tools": ["web_search", "web_crawl", "terminal_execute", "file_write", "file_read"],
    }])


def _plan_for_frontend(plan: List[PlanStep]) -> List[dict]:
    return [{**step, "description": step["content"], "tools": []} for step in plan]


def _todos_to_plan_steps(todos: List[Dict]) -> List[dict]:
    """
    将 agent 的 write_todos 输出转为前端 plan 步骤格式。
    这样中间件捕获的 todolist 变化可以实时推送给 PlanPanel，
    实现类似 Cursor 的 todo list 效果。
    """
    steps = []
    for i, todo in enumerate(todos):
        content = todo.get("content", "")
        status = todo.get("status", "pending")
        # 映射 todo status → plan step status
        if status in {"completed", "done"}:
            step_status = "completed"
        elif status in {"in_progress", "running"}:
            step_status = "in_progress"
        else:
            step_status = "pending"
        steps.append({
            "id": todo.get("id", f"T{i+1}"),
            "content": content,
            "description": content,
            "status": step_status,
            "tools": [],
        })
    return steps


# ───────────────────────────────────────────────────────────────────
# Deep Agent SSE 流
# ───────────────────────────────────────────────────────────────────

async def _arun_deep_agent_stream(
    session: ScienceSession, query: str, attachments: Optional[List[str]] = None,
    language: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """
    使用 deep_agent 执行对话，以 SSE 事件格式 yield。

    架构（参考 scienceclaw_agent_v5.py 的 stream_sse 方法）：
      - agent 内置 SSEMonitoringMiddleware，通过 wrap_tool_call 拦截工具前后
      - 中间件事件通过 middleware.drain_events() 在每个 stream chunk 后轮询
      - stream 本身只负责捕获 AI 的文本回复内容
      - 工具的参数/结果/耗时全部由中间件提供（更精准）
    """
    stream_start_time = time.time()

    # ---- 加载用户任务设置 ----
    user_id = getattr(session, "user_id", None)
    task_cfg: TaskSettings = await get_task_settings(user_id) if user_id else TaskSettings()

    # ---- 创建 agent + 中间件（会话级隔离，每个 session 独立工作目录）----
    agent, middleware, context_window, diagnostic = await deep_agent(
        session_id=session.session_id,
        model_config=getattr(session, "model_config", None),
        user_id=user_id,
        task_settings=task_cfg,
        diagnostic_enabled=DIAGNOSTIC_ENABLED,
        language=language,
    )
    middleware.clear()  # 确保干净状态
    middleware.set_required_skills(_infer_required_skills(query, attachments or [], session))
    for skill_evt in _yield_skill_events_from_middleware(middleware):
        yield skill_evt

    # ---- 发送初始 thinking 事件 ----
    yield {
        "event": "thinking",
        "data": {"content": ""},
    }

    # ---- 初始化 plan 变量（仅作为无 todos 时的兜底，不发送占位 plan 给前端） ----
    plan = _build_plan(query[:200])

    # ---- step_start（用于前端 process 分组，不影响 To-dos 显示） ----
    step = plan[0]
    yield {"event": "step_start", "data": {"step": step}}
    plan = normalize_plan_steps([{**step, "status": "in_progress"}])
    yield {"event": "plan_update", "data": {"plan": _plan_for_frontend(plan)}}

    # ---- 动态计算历史 token 预算（基于 context_window 和用户配置的 output_reserve）----
    history_token_budget = _compute_history_token_budget(
        context_window=context_window,
        output_reserve=task_cfg.output_reserve,
    )
    logger.info(
        f"[DeepAgent] context_window={context_window:,}, max_tokens={task_cfg.max_tokens:,}, "
        f"output_reserve={task_cfg.output_reserve:,}, history_budget={history_token_budget:,}"
    )

    # ---- 构建包含历史的消息列表（含工具调用上下文，排除当前 query 避免重复）----
    history_messages = _build_history_messages(
        session,
        current_query=query,
        max_rounds=task_cfg.max_history_rounds,
        max_history_tokens=history_token_budget,
    )
    logger.info(f"[DeepAgent] Loaded {len(history_messages)} history messages for session {session.session_id}")

    # ---- 流式执行 agent ----
    #
    # 关键改进（解决 stream 挂起导致结果不显示的问题）：
    #   1. 最终回复检测到后立即发送（不等 stream 结束）
    #   2. 中间件 todos 变化实时转为 plan 更新（Cursor 风格 todo list）
    #   3. 超时保护：stream 超过 5 分钟无新事件则强制结束
    #
    try:
        final_content = ""
        _last_thinking = ""

        enriched_query = query
        if attachments:
            file_list = "\n".join(f"  - {p}" for p in attachments)
            enriched_query = (
                f"{query}\n\n"
                f"[The user has uploaded the following files to the workspace. "
                f"You can read them directly using their absolute paths:\n{file_list}]"
            )

        input_messages = {"messages": history_messages + [HumanMessage(content=enriched_query)]}

        if diagnostic:
            diagnostic.save_initial_input(input_messages["messages"])

        # 中间件数据缓存
        _mw_cache: Dict[str, Dict] = {}

        from backend.deepagent.sse_protocol import get_protocol_manager
        protocol = get_protocol_manager()

        # Todos 追踪（中间件捕获的 write_todos → 转为 plan 步骤）
        _current_todos: List[Dict] = []

        import asyncio
        STREAM_TIMEOUT = task_cfg.agent_stream_timeout

        def _extract_chunk_text(chunk_msg) -> str:
            """从 AIMessageChunk 中提取可显示的文本（排除 thinking 标签内容）。"""
            content = chunk_msg.content
            if not content:
                return ""
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                return "".join(parts)
            if isinstance(content, str):
                return _THINK_TAG_RE.sub("", content)
            return ""

        # thread_id 让 deepagents SummarizationMiddleware 能跨请求累积压缩历史
        astream_config = {
            "configurable": {"thread_id": session.thread_id},
        }
        if diagnostic:
            astream_config["callbacks"] = [diagnostic.get_callback_handler()]

        _stream_ok = True  # 跟踪 stream 是否正常结束（超时/取消 → False）
        _chunks_had_reasoning = False  # messages 模式是否已发送过 reasoning_content
        _chunks_had_text = False       # messages 模式是否已发送过文本 chunk

        try:
            async with asyncio.timeout(STREAM_TIMEOUT):
              async for stream_event in agent.astream(
                  input_messages, stream_mode=["messages", "updates"],
                  config=astream_config,
              ):
                if session.is_cancelled():
                    _stream_ok = False
                    logger.info("Session cancelled during agent execution")
                    yield {"event": "error", "data": {"message": "Session stopped by user"}}
                    return

                stream_type, stream_data = stream_event

                # ──── 每次迭代都轮询中间件事件（确保 todos/tool 事件不因 messages 模式延迟） ────
                for mw_evt in middleware.drain_events():
                    mw_type = mw_evt.get("event", "")
                    mw_data = mw_evt.get("data", {})
                    call_id = mw_data.get("tool_call_id", "")

                    if mw_type == "middleware_tool_start":
                        _mw_cache.setdefault(call_id, {}).update({
                            "tool_meta": mw_data.get("tool_meta", {}),
                        })
                    elif mw_type == "middleware_tool_complete":
                        _mw_cache.setdefault(call_id, {}).update({
                            "duration_ms": mw_data.get("duration_ms"),
                            "tool_meta": mw_data.get("tool_meta", {}),
                        })
                    elif mw_type == "middleware_todos_update":
                        new_todos = mw_data.get("todos", [])
                        if new_todos and new_todos != _current_todos:
                            _current_todos = new_todos
                            plan_steps = _todos_to_plan_steps(new_todos)
                            yield {"event": "plan_update", "data": {"plan": plan_steps}}
                    elif mw_type == "middleware_skill_required":
                        yield {"event": "skill_required", "data": mw_data}
                    elif mw_type == "middleware_skill_read":
                        yield {"event": "skill_read", "data": mw_data}
                    elif mw_type == "middleware_skill_missing":
                        yield {"event": "skill_missing", "data": mw_data}

                # ──── messages 模式：逐 token 流式输出 ────
                if stream_type == "messages":
                    msg_chunk, metadata = stream_data
                    node_name = metadata.get("langgraph_node", "")

                    if "Middleware" in node_name:
                        continue

                    if isinstance(msg_chunk, AIMessageChunk):
                        reasoning = (msg_chunk.additional_kwargs or {}).get("reasoning_content", "")
                        if isinstance(reasoning, str) and reasoning:
                            _chunks_had_reasoning = True
                            yield {"event": "thinking", "data": {"content": reasoning}}

                        if getattr(msg_chunk, "tool_call_chunks", None):
                            continue

                        token_text = _extract_chunk_text(msg_chunk)

                        if token_text:
                            if len(token_text) > 2 and not token_text.strip() and '\n' in token_text:
                                token_text = "\n"
                            _chunks_had_text = True
                            yield {
                                "event": "thinking",
                                "data": {"content": token_text},
                            }

                    continue  # messages 模式处理完毕，跳过 updates 逻辑

                # ──── updates 模式：完整节点输出（工具调用、计划等） ────
                chunk = stream_data

                # 处理 updates 模式的 chunk
                for node_name, node_output in chunk.items():
                    if "Middleware" in node_name:
                        continue

                    messages = []
                    if isinstance(node_output, dict):
                        messages = node_output.get("messages", [])
                    elif isinstance(node_output, list):
                        messages = node_output
                    if hasattr(messages, "value"):
                        messages = messages.value

                    for msg in messages:
                        extra = ""
                        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                            tool_names = [tc.get("name", "?") for tc in msg.tool_calls]
                            extra = f" tool_calls={tool_names}"
                        elif isinstance(msg, ToolMessage):
                            extra = f" tool={getattr(msg, 'name', '?')}"
                        logger.debug(f"[DeepAgent] node={node_name} msg_type={type(msg).__name__}{extra}")

                        if isinstance(msg, AIMessage):
                            # 提取 token 使用量
                            token_info = _extract_token_usage(msg)
                            if token_info["input_tokens"] or token_info["output_tokens"]:
                                logger.debug(f"[DeepAgent] Token usage from message: input={token_info['input_tokens']}, output={token_info['output_tokens']}")
                                middleware.add_tokens(token_info["input_tokens"], token_info["output_tokens"])

                            _thinking_text, _clean_text = _extract_thinking(msg)
                            if _thinking_text:
                                _last_thinking = _thinking_text
                            # 仅当 messages 模式未发送过对应内容时才补发（避免重复）
                            # Claude content blocks 中的 thinking 不走 messages 模式，需在此补发
                            if _thinking_text and not _chunks_had_reasoning:
                                yield {
                                    "event": "thinking",
                                    "data": {"content": _thinking_text},
                                }
                            if _clean_text and getattr(msg, "tool_calls", None) and not _chunks_had_text:
                                yield {"event": "thinking", "data": {"content": _clean_text}}

                            # 重置标记，为下一轮 AI 消息（工具调用后的新回复）做准备
                            _chunks_had_reasoning = False
                            _chunks_had_text = False

                        # AIMessage with tool_calls → yield tool_call
                        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                            for tc in msg.tool_calls:
                                call_id = tc.get("id", uuid.uuid4().hex)
                                fn_name = tc.get("name", "unknown")
                                fn_args = tc.get("args", {})
                                cached = _mw_cache.get(call_id, {})
                                tool_meta = cached.get("tool_meta") or protocol.get_tool_meta(fn_name)
                                yield {
                                    "event": "tool_call",
                                    "data": {
                                        "tool_call_id": call_id,
                                        "function": fn_name,
                                        "args": fn_args,
                                        "description": f"{fn_name}: {json.dumps(fn_args, ensure_ascii=False)[:200]}",
                                        "tool_meta": tool_meta,
                                    },
                                }

                        elif isinstance(msg, ToolMessage):
                            content = msg.content
                            if isinstance(content, str) and len(content) > 3000:
                                content = content[:3000] + "... (truncated)"
                            tool_call_id = getattr(msg, "tool_call_id", "")
                            fn_name = getattr(msg, "name", "")
                            cached = _mw_cache.pop(tool_call_id, {})
                            duration_ms = cached.get("duration_ms")
                            tool_meta = cached.get("tool_meta") or protocol.get_tool_meta(fn_name)
                            yield {
                                "event": "tool_result",
                                "data": {
                                    "tool_call_id": tool_call_id,
                                    "function": fn_name,
                                    "content": content,
                                    "duration_ms": duration_ms,
                                    "tool_meta": tool_meta,
                                },
                            }

                        # 无 tool_calls 的 AIMessage = 最终回复
                        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                            _, _clean = _extract_thinking(msg)
                            if _clean:
                                final_content = _clean

        except (asyncio.TimeoutError, TimeoutError):
            _stream_ok = False
            logger.warning(f"[DeepAgent] Stream timed out after {STREAM_TIMEOUT}s")
            yield {"event": "error", "data": {"message": f"Agent execution timed out after {STREAM_TIMEOUT}s"}}

        for skill_evt in _yield_skill_events_from_middleware(middleware):
            yield skill_evt

        # ---- stream 结束后的收尾 ----
        # 只有 stream 正常结束才将未完成步骤标记为 completed；
        # 超时/取消时保留实际状态（pending/in_progress → failed）。
        if _current_todos:
            final_plan_steps = _todos_to_plan_steps(_current_todos)
            if _stream_ok:
                for step in final_plan_steps:
                    if step["status"] != "completed":
                        step["status"] = "completed"
            else:
                for step in final_plan_steps:
                    if step["status"] not in ("completed", "pending"):
                        step["status"] = "failed"
            yield {"event": "plan_update", "data": {"plan": final_plan_steps}}
        else:
            end_status = "completed" if _stream_ok else "failed"
            plan = normalize_plan_steps([{**plan[0], "status": end_status}])
            session.set_plan(plan)
            yield {"event": "plan_update", "data": {"plan": _plan_for_frontend(plan)}}
        yield {"event": "step_end", "data": {"step_id": "S1"}}

        # 发送最终回复到中间聊天区
        if final_content:
            yield {
                "event": "planning_message",
                "data": {"type": "assistant", "content": final_content},
            }
        elif _last_thinking:
            logger.warning("[DeepAgent] Model returned only thinking content with no text response, using thinking as fallback")
            yield {
                "event": "planning_message",
                "data": {"type": "assistant", "content": _last_thinking},
            }
        else:
            logger.warning("[DeepAgent] Model returned completely empty response")
            yield {
                "event": "planning_message",
                "data": {"type": "assistant", "content": "No response generated."},
            }

        # ---- 统计信息 ----
        total_duration_ms = int((time.time() - stream_start_time) * 1000)
        mw_stats = middleware.get_statistics()
        logger.info(f"[DeepAgent] Statistics: duration={total_duration_ms}ms, tool_calls={mw_stats.get('total_tool_calls', 0)}, input_tokens={mw_stats.get('input_tokens', 0)}, output_tokens={mw_stats.get('output_tokens', 0)}")
        yield {
            "event": "statistics",
            "data": {
                "total_duration_ms": total_duration_ms,
                "tool_call_count": mw_stats.get("total_tool_calls", 0),
                "total_tool_duration_ms": mw_stats.get("total_tool_duration_ms", 0),
                "input_tokens": mw_stats.get("input_tokens", 0),
                "output_tokens": mw_stats.get("output_tokens", 0),
                "token_count": mw_stats.get("total_tokens", 0),
            },
        }

        # ---- 诊断摘要（DIAGNOSTIC_MODE=1 时生效）----
        if diagnostic:
            try:
                diagnostic.save_summary()
            except Exception:
                logger.warning("[Diagnostic] Failed to save summary", exc_info=True)

    except Exception as exc:
        logger.exception("DeepAgent runner failed")
        # 报错时先下发 plan_update 将当前步骤标为 failed，避免前端仍显示「推理完成」且任务进度一直旋转
        try:
            if _current_todos:
                failed_plan_steps = _todos_to_plan_steps(_current_todos)
                for step in failed_plan_steps:
                    if step.get("status") not in ("completed", "done"):
                        step["status"] = "failed"
                yield {"event": "plan_update", "data": {"plan": failed_plan_steps}}
            else:
                failed_plan = normalize_plan_steps([{**plan[0], "status": "failed"}])
                yield {"event": "plan_update", "data": {"plan": _plan_for_frontend(failed_plan)}}
            # 不发送 step_end，避免 session 层将其映射为 completed 覆盖 failed 状态
        except NameError:
            # _current_todos/plan 未定义（异常发生在 stream 之前）时跳过
            pass
        err_type = type(exc).__name__
        err_msg = str(exc)
        err_lower = err_msg.lower()
        if "context length" in err_lower or "context_length_exceeded" in err_lower or "maximum context" in err_lower:
            user_msg = (
                "对话上下文过长，超出模型上下文窗口限制。"
                "请开启新会话继续。"
                "(Context length exceeded. Please start a new session.)"
            )
        elif "Connection" in err_type or "connection" in err_lower or "timeout" in err_lower:
            user_msg = "网络连接异常，请检查网络后重试。(Network connection error, please retry.)"
        elif "APIConnectionError" in err_type:
            user_msg = "无法连接到 AI 服务，请稍后重试。(Cannot reach AI service, please retry later.)"
        elif "RateLimitError" in err_type or "rate_limit" in err_lower:
            user_msg = "请求过于频繁，请稍后重试。(Rate limited, please retry later.)"
        elif "AuthenticationError" in err_type:
            user_msg = "API 密钥无效，请检查配置。(Invalid API key, please check configuration.)"
        else:
            user_msg = f"任务执行出错：{err_msg}"
        yield {"event": "error", "data": {"message": user_msg}}


# ───────────────────────────────────────────────────────────────────
# Eval 执行器（内部调用，非 SSE）
# ───────────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    """单个 eval 测试用例的执行结果。"""
    prompt: str
    response: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    error: Optional[str] = None


async def run_eval_task(
    session_id: str,
    query: str,
    model_config: Optional[Dict[str, Any]] = None,
    skill_sources: Optional[List[str]] = None,
    timeout: int = 300,
) -> EvalResult:
    """
    在独立的 eval Agent 中运行单个测试用例，收集完整输出。

    与 _arun_deep_agent_stream 的区别：
      - 使用 deep_agent_eval() 创建精简 Agent
      - 不 yield SSE 事件，直接收集全部输出
      - 返回结构化的 EvalResult
    """
    import asyncio
    start_time = time.time()
    result = EvalResult(prompt=query)

    try:
        agent, middleware = await deep_agent_eval(
            session_id=session_id,
            model_config=model_config,
            skill_sources=skill_sources,
        )
        middleware.clear()
        middleware.set_required_skills(_infer_required_skills(query, [], None))

        input_messages = {"messages": [HumanMessage(content=query)]}

        tool_calls_collected: List[Dict[str, Any]] = []
        final_text_parts: List[str] = []

        try:
            async with asyncio.timeout(timeout):
                async for stream_event in agent.astream(
                    input_messages, stream_mode=["messages", "updates"]
                ):
                    stream_type, stream_data = stream_event

                    if stream_type == "updates":
                        chunk = stream_data
                        for node_name, node_output in chunk.items():
                            if "Middleware" in node_name:
                                continue
                            messages = []
                            if isinstance(node_output, dict):
                                messages = node_output.get("messages", [])
                            elif isinstance(node_output, list):
                                messages = node_output
                            if hasattr(messages, "value"):
                                messages = messages.value

                            for msg in messages:
                                if isinstance(msg, AIMessage):
                                    if getattr(msg, "tool_calls", None):
                                        for tc in msg.tool_calls:
                                            tool_calls_collected.append({
                                                "name": tc.get("name", "unknown"),
                                                "args": tc.get("args", {}),
                                            })
                                    else:
                                        _, clean = _extract_thinking(msg)
                                        if clean:
                                            final_text_parts.append(clean)

                                elif isinstance(msg, ToolMessage):
                                    content = msg.content
                                    if isinstance(content, str) and len(content) > 3000:
                                        content = content[:3000] + "... (truncated)"
                                    tool_calls_collected.append({
                                        "name": getattr(msg, "name", ""),
                                        "result": content,
                                    })
        except (asyncio.TimeoutError, TimeoutError):
            result.error = f"Eval timed out after {timeout}s"

        result.response = "\n".join(final_text_parts)
        result.tool_calls = tool_calls_collected

    except Exception as exc:
        logger.exception(f"[EvalRunner] Failed for session={session_id}")
        result.error = f"{type(exc).__name__}: {exc}"

    result.duration_ms = int((time.time() - start_time) * 1000)
    return result


# ───────────────────────────────────────────────────────────────────
# 对外入口（drop-in replacement）
# ───────────────────────────────────────────────────────────────────

async def arun_science_task_stream(
    session: ScienceSession, query: str, attachments: Optional[List[str]] = None,
    language: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """对话任务流入口，所有模式统一走 DeepAgent。"""
    async for evt in _arun_deep_agent_stream(session, query, attachments, language=language):
        yield evt
