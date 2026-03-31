"""
工具结果自动落盘中间件 — Cursor 风格。

当工具返回的结果超过阈值时，自动将完整结果写入工作区文件，
返回给 Agent 的 ToolMessage 改为摘要 + 文件路径引用。
Agent 在需要完整数据时可以用 read_file 按需读取。

这解决了多轮对话中工具结果在历史中被截断导致信息丢失的问题。
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any, Callable, Optional, Set

from loguru import logger
from langchain.agents.middleware import AgentMiddleware


_OFFLOAD_THRESHOLD = 3000
_SUMMARY_LENGTH = 1500
_OFFLOAD_DIR = "research_data"

_OFFLOAD_TOOLS: Set[str] = {
    "web_search", "web_crawl",
    "execute", "sandbox_exec", "terminal_execute",
    "tooluniverse_run",
}

_RELAXED_OFFLOAD_TOOLS: Set[str] = {
    "read_file", "edit_file", "ls", "glob", "grep",
}
_RELAXED_OFFLOAD_THRESHOLD = 30000


def _extract_text(result: Any) -> Optional[str]:
    """Extract string content from various tool result formats."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("content", "output", "text", "result"):
            val = result.get(key)
            if isinstance(val, str) and len(val) > 100:
                return val
    if hasattr(result, "content"):
        c = result.content
        if isinstance(c, str):
            return c
    return None


def _make_summary(text: str, file_path: str) -> str:
    """Create a summary with file reference for the agent."""
    preview = text[:_SUMMARY_LENGTH]
    if len(text) > _SUMMARY_LENGTH:
        preview += "\n..."
    return (
        f"[Full result saved to {file_path} ({len(text)} chars). "
        f"Use read_file(\"{file_path}\") to access complete data. "
        f"NOTE: This file contains raw tool output. To use in sandbox scripts, "
        f"first read_file it, extract the data you need, then write_file a clean JSON file.]\n\n"
        f"{preview}"
    )


def _safe_filename_component(value: str) -> str:
    cleaned = str(value or "").strip()
    cleaned = cleaned.replace("\\", " ").replace("/", " ")
    for char in '<>:"|?*\r\n':
        cleaned = cleaned.replace(char, " ")
    cleaned = "_".join(part for part in cleaned.split() if part)
    return cleaned[:120] or "result"


def _extract_title_candidate(result: Any) -> Optional[str]:
    if isinstance(result, dict):
        for key in ("suggested_title", "topic", "title"):
            value = str(result.get(key, "")).strip()
            if value:
                return value
        review_note_path = str(result.get("review_note_path", "")).strip()
        if review_note_path:
            return Path(review_note_path).stem
        for key in ("data", "result"):
            nested = result.get(key)
            if isinstance(nested, dict):
                nested_title = _extract_title_candidate(nested)
                if nested_title:
                    return nested_title
    return None


class ToolResultOffloadMiddleware(AgentMiddleware):
    """Automatically offload large tool results to workspace files."""

    def __init__(self, workspace_dir: str, backend: Any):
        super().__init__()
        self._workspace = workspace_dir
        self._backend = backend
        self._offload_count = 0
        self._diagnostic = None  # Optional[DiagnosticLogger], set externally

    def _should_offload(self, tool_name: Optional[str], text: Optional[str]) -> bool:
        if not tool_name or not text:
            return False
        if len(text) < _OFFLOAD_THRESHOLD:
            return False
        if tool_name in _RELAXED_OFFLOAD_TOOLS:
            return len(text) > _RELAXED_OFFLOAD_THRESHOLD
        if tool_name in _OFFLOAD_TOOLS:
            return True
        return len(text) > _OFFLOAD_THRESHOLD * 2

    def _make_file_path(self, tool_name: str, tool_call_id: str, result: Any) -> str:
        short_id = hashlib.md5(
            f"{tool_call_id}{time.time()}".encode()
        ).hexdigest()[:8]
        safe_name = tool_name.replace("/", "_").replace(" ", "_")
        title_candidate = _extract_title_candidate(result)
        if title_candidate:
            safe_title = _safe_filename_component(title_candidate)
            return f"{self._workspace}/{_OFFLOAD_DIR}/{safe_title}__{safe_name}_{short_id}.md"
        return f"{self._workspace}/{_OFFLOAD_DIR}/{safe_name}_{short_id}.md"

    async def _offload_result(
        self, tool_name: str, tool_call_id: str, text: str, result: Any
    ) -> str:
        file_path = self._make_file_path(tool_name, tool_call_id, result)
        try:
            await self._backend.awrite(file_path, text)
            self._offload_count += 1
            logger.info(
                f"[Offload] {tool_name} result ({len(text)} chars) → {file_path}"
            )
            summary = _make_summary(text, file_path)
            if self._diagnostic:
                self._diagnostic.log_offload(
                    tool_name, len(text), len(summary), file_path,
                )
            return summary
        except Exception as exc:
            logger.warning(f"[Offload] Failed to write {file_path}: {exc}")
            return text

    def _extract_tool_info(self, request: Any) -> tuple:
        tool_name = None
        tool_call_id = ""
        if hasattr(request, "tool_call"):
            tc = request.tool_call
            if isinstance(tc, dict):
                tool_name = tc.get("name")
                tool_call_id = tc.get("id", "")
        elif isinstance(request, dict):
            tool_name = request.get("name")
            tool_call_id = request.get("id", "")
        return tool_name, tool_call_id

    def _replace_result_text(self, result: Any, new_text: str) -> Any:
        """Replace the text content in the result while preserving structure."""
        if isinstance(result, str):
            return new_text
        if isinstance(result, dict):
            for key in ("content", "output", "text", "result"):
                if key in result and isinstance(result[key], str):
                    result = dict(result)
                    result[key] = new_text
                    return result
        if hasattr(result, "content") and isinstance(result.content, str):
            result.content = new_text
            return result
        return new_text

    def wrap_tool_call(self, request: Any, handler: Callable) -> Any:
        result = handler(request)
        tool_name, tool_call_id = self._extract_tool_info(request)
        text = _extract_text(result)
        if self._should_offload(tool_name, text):
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    summary = pool.submit(
                        asyncio.run,
                        self._offload_result(tool_name, tool_call_id, text, result)
                    ).result()
            else:
                summary = asyncio.run(
                    self._offload_result(tool_name, tool_call_id, text, result)
                )
            return self._replace_result_text(result, summary)
        return result

    async def awrap_tool_call(self, request: Any, handler: Callable) -> Any:
        result = await handler(request)
        tool_name, tool_call_id = self._extract_tool_info(request)
        text = _extract_text(result)
        if self._should_offload(tool_name, text):
            summary = await self._offload_result(tool_name, tool_call_id, text, result)
            return self._replace_result_text(result, summary)
        return result
