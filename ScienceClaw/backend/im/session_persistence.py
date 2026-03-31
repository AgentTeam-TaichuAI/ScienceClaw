from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Sequence

import shortuuid
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from backend.deepagent.engine import get_llm_model
from backend.deepagent.sessions import ScienceSession


def now_ts() -> int:
    return int(time.time())


def new_event_id() -> str:
    return shortuuid.uuid()


def wrap_event(event: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"event": event, "data": data}


def append_session_event(session: ScienceSession, event: Dict[str, Any]) -> None:
    events = getattr(session, "events", None)
    if not isinstance(events, list):
        events = []
        setattr(session, "events", events)
    events.append(event)
    if event.get("event") == "message":
        data = event.get("data") or {}
        content = data.get("content")
        if isinstance(content, str) and content.strip():
            setattr(session, "latest_message", content)
            setattr(session, "latest_message_at", int(data.get("timestamp") or now_ts()))


def count_user_messages(events: List[Dict[str, Any]]) -> int:
    if not events:
        return 0
    return sum(
        1
        for event in events
        if event.get("event") == "message" and (event.get("data") or {}).get("role") == "user"
    )


async def maybe_generate_session_title(session: ScienceSession, first_message: str) -> str:
    prompt = (first_message or "").strip()
    if not prompt or (getattr(session, "title", None) or "").strip():
        return ""
    if count_user_messages(getattr(session, "events", []) or []) > 1:
        return ""

    if len(prompt) > 800:
        prompt = prompt[:800] + "..."
    system = (
        "You are a helper. Given the first user message of a chat conversation, "
        "reply with a very short summary to use as the chat title. "
        "Use at most 15 words. Reply in the same language as the user. "
        "Output only the title, no quotes, no explanation, no prefix."
    )
    try:
        llm = get_llm_model(config=None, max_tokens_override=60, streaming=False)
        response = await llm.ainvoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=prompt),
            ]
        )
        title = (response.content or "").strip()
        if title and len(title) > 80:
            title = title[:80].rstrip()
        if title:
            session.title = title
            await session.save()
        return title or ""
    except Exception as exc:
        logger.warning("im session title generation failed: {}", exc)
        first_line = prompt.split("\n")[0].strip()
        fallback = first_line[:50] if first_line else ""
        if fallback:
            session.title = fallback
            await session.save()
        return fallback


async def persist_user_message(session: ScienceSession, content: str, attachments: Sequence[str] | None = None) -> None:
    if not (content or "").strip() and not attachments:
        return
    append_session_event(
        session,
        wrap_event(
            "message",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "content": content,
                "role": "user",
                "attachments": list(attachments or []),
            },
        ),
    )
    session.status = "running"
    await session.save()


def _map_plan_status(status: str) -> str:
    normalized = (status or "pending").strip()
    if normalized in {"in_progress", "running"}:
        return "running"
    if normalized == "completed":
        return "completed"
    if normalized in {"blocked", "failed"}:
        return "failed"
    return "pending"


def _map_plan_steps(plan: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "event_id": new_event_id(),
            "timestamp": now_ts(),
            "status": _map_plan_status(str(step.get("status") or "pending")),
            "id": str(step.get("id") or ""),
            "description": str(step.get("content") or ""),
            "tools": step.get("tools") if isinstance(step.get("tools"), list) else [],
        }
        for step in plan
    ]


def _infer_tool_name(tool_function: str) -> str:
    func = (tool_function or "").strip()
    if func in {"web_search", "web_crawl", "internet_search"}:
        return "web_search"
    if func in {"sandbox_exec", "terminal_execute", "terminal_session", "sandbox_execute_bash", "sandbox_execute_code"}:
        return func
    if func in {"sandbox_write_file", "file_write", "sandbox_file_operations", "sandbox_str_replace_editor"}:
        return func
    if func in {"sandbox_read_file", "file_read"}:
        return func
    if func in {"sandbox_find_files", "file_list"}:
        return func
    if func == "file_search":
        return "grep"
    if func == "file_replace":
        return "edit_file"
    if func == "terminal_kill":
        return "execute"
    if func in {"sandbox_get_context", "sandbox_get_packages", "sandbox_convert_to_markdown"}:
        return func
    if func.startswith("sandbox_browser_") or func == "sandbox_get_browser_info":
        return func
    if func.startswith("browser_") or func.startswith("markitdown_"):
        return func
    if func in {"ls", "grep", "write", "read_file", "write_file", "edit_file"}:
        return func
    return func or "info"


def _normalize_tool_args(tool_function: str, args: Any, tool_call_id: str) -> Dict[str, Any]:
    if not isinstance(args, dict):
        return {}
    out = dict(args)
    func = (tool_function or "").strip()
    if func in {
        "read_file",
        "write_file",
        "edit_file",
        "sandbox_read_file",
        "sandbox_write_file",
        "file_read",
        "file_write",
        "file_replace",
    }:
        if "file" not in out and "file_path" in out:
            out["file"] = out.get("file_path")
    if func in {"execute", "sandbox_exec", "terminal_execute"}:
        out.setdefault("id", tool_call_id)
    return out


def _maybe_wrap_tool_content(
    tool_function: str,
    tool_args: Dict[str, Any],
    raw_content: Any,
    tool_call_id: str,
) -> Any:
    func = (tool_function or "").strip()
    if func in {"execute", "sandbox_exec", "terminal_execute"}:
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
            except (TypeError, json.JSONDecodeError):
                parsed = {"output": raw_content}
        elif isinstance(raw_content, dict):
            parsed = raw_content
        else:
            parsed = {"output": str(raw_content)}
        output = parsed.get("output", str(raw_content))
        command = tool_args.get("command", "")
        session_id = parsed.get("session_id", tool_call_id)
        return {
            "output": output,
            "session_id": session_id,
            "console": [{"ps1": "$", "command": command, "output": output}],
        }
    if func in {"read_file", "sandbox_read_file", "file_read"}:
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                return {
                    "file": parsed.get("file", tool_args.get("file_path", "")),
                    "content": parsed.get("content", ""),
                }
            except (TypeError, json.JSONDecodeError):
                pass
        elif isinstance(raw_content, dict):
            return {
                "file": raw_content.get("file", tool_args.get("file_path", "")),
                "content": raw_content.get("content", ""),
            }
        return {
            "file": tool_args.get("file", tool_args.get("file_path", "")),
            "content": raw_content if isinstance(raw_content, str) else str(raw_content),
        }
    if func in {"write_file", "sandbox_write_file", "file_write"} and isinstance(raw_content, str):
        try:
            return json.loads(raw_content)
        except (TypeError, json.JSONDecodeError):
            return raw_content
    return raw_content


def _extract_tool_meta(data: Dict[str, Any]) -> Dict[str, Any]:
    meta = data.get("tool_meta") or {}
    result: Dict[str, Any] = {
        "icon": meta.get("icon", ""),
        "category": meta.get("category", ""),
        "description": meta.get("description", ""),
    }
    if meta.get("sandbox"):
        result["sandbox"] = True
    return result


async def persist_thinking_event(session: ScienceSession, content: str) -> None:
    if not (content or "").strip():
        return
    append_session_event(
        session,
        wrap_event(
            "thinking",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "content": content,
            },
        ),
    )
    await session.save()


async def persist_plan_event(session: ScienceSession, plan: Sequence[Dict[str, Any]] | None) -> None:
    if not isinstance(plan, list):
        return
    append_session_event(
        session,
        wrap_event(
            "plan",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "steps": _map_plan_steps(plan),
            },
        ),
    )
    await session.save()


async def persist_step_event(session: ScienceSession, step_id: str, description: str, status: str) -> None:
    normalized_status = _map_plan_status(status)
    if not step_id and not description:
        return
    append_session_event(
        session,
        wrap_event(
            "step",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "status": normalized_status,
                "id": step_id,
                "description": description,
            },
        ),
    )
    await session.save()


async def persist_tool_call_event(session: ScienceSession, data: Dict[str, Any]) -> None:
    tool_call_id = str(data.get("tool_call_id") or "")
    tool_function = str(data.get("function") or "")
    append_session_event(
        session,
        wrap_event(
            "tool",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "tool_call_id": tool_call_id,
                "name": _infer_tool_name(tool_function),
                "status": "calling",
                "function": tool_function,
                "args": _normalize_tool_args(tool_function, data.get("args") or {}, tool_call_id),
                "tool_meta": _extract_tool_meta(data),
            },
        ),
    )
    await session.save()


async def persist_tool_result_event(session: ScienceSession, data: Dict[str, Any]) -> None:
    tool_call_id = str(data.get("tool_call_id") or "")
    tool_function = str(data.get("function") or "")
    raw_args = data.get("args")
    tool_args = _normalize_tool_args(tool_function, raw_args or {}, tool_call_id) if raw_args else None
    payload: Dict[str, Any] = {
        "event_id": new_event_id(),
        "timestamp": now_ts(),
        "tool_call_id": tool_call_id,
        "name": _infer_tool_name(tool_function),
        "status": "called",
        "function": tool_function,
        "content": _maybe_wrap_tool_content(tool_function, tool_args or {}, data.get("content"), tool_call_id),
        "tool_meta": _extract_tool_meta(data),
    }
    if tool_args:
        payload["args"] = tool_args
    duration_ms = data.get("duration_ms")
    if isinstance(duration_ms, (int, float)):
        payload["duration_ms"] = duration_ms
    append_session_event(session, wrap_event("tool", payload))
    await session.save()


async def persist_assistant_message(
    session: ScienceSession,
    content: str,
    attachments: Sequence[str] | None = None,
) -> None:
    if not (content or "").strip() and not attachments:
        return
    append_session_event(
        session,
        wrap_event(
            "message",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "content": content,
                "role": "assistant",
                "attachments": list(attachments or []),
            },
        ),
    )
    await session.save()


async def persist_error_message(session: ScienceSession, error_message: str) -> None:
    append_session_event(
        session,
        wrap_event(
            "error",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "error": error_message,
            },
        ),
    )
    session.status = "completed"
    await session.save()


async def persist_done_event(
    session: ScienceSession,
    statistics: Dict[str, Any] | None = None,
    round_files: Sequence[Dict[str, Any]] | None = None,
) -> None:
    append_session_event(
        session,
        wrap_event(
            "done",
            {
                "event_id": new_event_id(),
                "timestamp": now_ts(),
                "statistics": statistics or {},
                "round_files": list(round_files or []),
            },
        ),
    )
    session.status = "completed"
    await session.save()
