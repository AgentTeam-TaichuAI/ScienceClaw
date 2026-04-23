"""
Tools/ 目录：外部扩展工具的自动发现与沙箱代理执行。

方案 C 架构：
  - 使用 AST 静态解析 .py 文件，提取 @tool 元数据（不在 Backend 中 import 模块）
  - 创建 LangChain StructuredTool 代理，调用时通过 REST API 发送给 Sandbox 容器执行
  - 测试环境 = 生产环境，彻底消除 Backend 与 Sandbox 的包不一致问题
"""
from __future__ import annotations

import ast
import json
import logging
import os
import shlex
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.tools import StructuredTool
from pydantic import Field, create_model

logger = logging.getLogger(__name__)

_package_dir = str(Path(__file__).resolve().parent)

_lock = threading.Lock()
_cached_tools: list[StructuredTool] = []

_SANDBOX_REST_URL = os.environ.get("SANDBOX_REST_URL", "http://localhost:18080").rstrip("/")
_TOOL_RUNNER_PATH = "/app/_tool_runner.py"
_TOOLS_DIR_IN_SANDBOX = "/app/Tools"
_EXECUTE_TIMEOUT = 120

_START_MARKER = ">>>TOOL_RESULT_JSON>>>"
_END_MARKER = "<<<TOOL_RESULT_JSON<<<"


# ── Sandbox session management (fresh session per proxy call) ──

def _create_sandbox_session(exec_dir: str = "/") -> str:
    resp = httpx.post(
        f"{_SANDBOX_REST_URL}/v1/shell/sessions/create",
        json={"exec_dir": exec_dir},
        timeout=10,
        trust_env=False,
    )
    resp.raise_for_status()
    session_id = resp.json()["data"]["session_id"]
    logger.info(f"[Tools] Sandbox tool-exec session: {session_id}")
    return session_id


def _write_sandbox_file(file_path: str, content: str) -> None:
    resp = httpx.post(
        f"{_SANDBOX_REST_URL}/v1/file/write",
        json={"file": file_path, "content": content},
        timeout=15,
        trust_env=False,
    )
    resp.raise_for_status()


def _execute_in_sandbox(command: str, timeout: int = _EXECUTE_TIMEOUT) -> str:
    """Execute a shell command in the sandbox, return stdout for this call only."""

    def _do_exec() -> str:
        sid = _create_sandbox_session()
        resp = httpx.post(
            f"{_SANDBOX_REST_URL}/v1/shell/exec",
            json={"id": sid, "command": command, "async_mode": False},
            timeout=timeout + 5,
            trust_env=False,
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("output", "")

    try:
        return _do_exec()
    except Exception as exc:
        logger.warning(f"[Tools] Sandbox exec failed ({exc}), retrying with fresh session")
        return _do_exec()


# ── AST helpers ──

_SIMPLE_TYPES: Dict[str, type] = {
    "str": str, "int": int, "float": float, "bool": bool,
    "dict": dict, "list": list, "Dict": dict, "List": list, "Any": Any,
}


def _resolve_type(node: ast.expr | None) -> type:
    if node is None:
        return str
    if isinstance(node, ast.Name):
        return _SIMPLE_TYPES.get(node.id, Any)
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name):
            base = node.value.id
            if base in ("Dict", "dict"):
                return dict
            if base in ("List", "list"):
                return list
            if base == "Optional":
                return Optional[_resolve_type(node.slice)]  # type: ignore[misc]
        return Any
    if isinstance(node, ast.Attribute):
        return Any
    if isinstance(node, ast.Constant):
        return type(node.value)
    return Any


def _resolve_default(node: ast.expr) -> Any:
    """Return the default value, or Ellipsis (...) when there is none."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id == "None":
        return None
    if isinstance(node, ast.List):
        return []
    if isinstance(node, ast.Dict):
        return {}
    return ...


def _parse_tool_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Parse a .py file using AST; extract the first @tool function's metadata."""
    try:
        source = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception as exc:
        logger.warning(f"[Tools] AST parse failed for {file_path}: {exc}")
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        has_tool_decorator = any(
            (isinstance(d, ast.Name) and d.id == "tool")
            or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "tool")
            for d in node.decorator_list
        )
        if not has_tool_decorator:
            continue

        func_name = node.name
        docstring = ast.get_docstring(node) or f"Tool: {func_name}"

        args_node = node.args
        num_defaults = len(args_node.defaults)
        num_args = len(args_node.args)
        params: list[dict] = []
        for i, arg in enumerate(args_node.args):
            if arg.arg == "self":
                continue
            ptype = _resolve_type(arg.annotation)
            default_idx = i - (num_args - num_defaults)
            pdefault = _resolve_default(args_node.defaults[default_idx]) if default_idx >= 0 else ...
            params.append({"name": arg.arg, "type": ptype, "default": pdefault})

        return {
            "func_name": func_name,
            "docstring": docstring,
            "params": params,
            "file_path": file_path,
        }

    return None


# ── Proxy tool creation ──

def _create_proxy_tool(meta: Dict[str, Any]) -> StructuredTool:
    func_name: str = meta["func_name"]
    docstring: str = meta["docstring"]
    params: list[dict] = meta["params"]
    file_path: str = meta["file_path"]

    fields: dict = {}
    for p in params:
        ptype = p["type"]
        pdefault = p["default"]
        if pdefault is not ...:
            if pdefault is None:
                fields[p["name"]] = (Optional[ptype], Field(default=pdefault))  # type: ignore[valid-type]
            else:
                fields[p["name"]] = (ptype, Field(default=pdefault))
        else:
            fields[p["name"]] = (ptype, ...)

    input_model = create_model(f"{func_name}_input", **fields)

    tool_basename = Path(file_path).name
    sandbox_tool_path = f"{_TOOLS_DIR_IN_SANDBOX}/{tool_basename}"

    def _make_proxy(fn: str, path: str):
        def _proxy_run(**kwargs: Any) -> Any:
            args_json = json.dumps(kwargs, ensure_ascii=False, default=str)
            args_path = f"/tmp/scienceclaw_tool_args_{uuid.uuid4().hex}.json"
            try:
                _write_sandbox_file(args_path, args_json)
            except Exception as exc:
                logger.error(f"[Tools] Sandbox file write failed for {fn}: {exc}")
                return {
                    "_sandbox_exec": {"command": "", "output": str(exc)},
                    "result": {"error": f"Sandbox file write failed: {exc}"},
                }

            cmd = (
                f"python3 {shlex.quote(_TOOL_RUNNER_PATH)} "
                f"{shlex.quote(path)} {shlex.quote(fn)} --args-file {shlex.quote(args_path)}"
            )
            logger.info(f"[Tools] Proxy → sandbox: {fn}")
            try:
                raw_output = _execute_in_sandbox(cmd)
            except Exception as exc:
                logger.error(f"[Tools] Sandbox call failed for {fn}: {exc}")
                return {
                    "_sandbox_exec": {"command": cmd, "output": str(exc)},
                    "result": {"error": f"Sandbox execution failed: {exc}"},
                }

            start = raw_output.rfind(_START_MARKER)
            end = raw_output.rfind(_END_MARKER)
            if start == -1 or end == -1 or end < start:
                logger.error(f"[Tools] Result markers missing for {fn}")
                return {
                    "_sandbox_exec": {"command": cmd, "output": raw_output[-2000:]},
                    "result": {"error": "Tool output parsing failed"},
                }

            pre_output = raw_output[:start].strip()
            json_str = raw_output[start + len(_START_MARKER):end].strip()
            try:
                parsed = json.loads(json_str)
            except json.JSONDecodeError:
                parsed = {"error": "Invalid JSON in tool result", "raw": json_str[:500]}

            return {
                "_sandbox_exec": {"command": cmd, "output": pre_output},
                "result": parsed,
            }
        return _proxy_run

    _proxy_run = _make_proxy(func_name, sandbox_tool_path)

    return StructuredTool(
        name=func_name,
        description=docstring,
        func=_proxy_run,
        args_schema=input_model,
    )


# ── Scanning ──

def _scan_and_create_proxies() -> list[StructuredTool]:
    tools_dir = Path(_package_dir)
    tools: list[StructuredTool] = []
    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_") or py_file.name == "__init__.py":
            continue
        meta = _parse_tool_file(str(py_file))
        if meta is None:
            logger.warning(f"[Tools] No @tool found in {py_file.name}, skipping")
            continue
        try:
            proxy = _create_proxy_tool(meta)
            tools.append(proxy)
            logger.info(f"[Tools] Proxy ready: {proxy.name} ← {py_file.name}")
        except Exception as exc:
            logger.warning(f"[Tools] Proxy creation failed for {py_file.name}: {exc}")
    return tools


def reload_external_tools(force: bool = False) -> list[StructuredTool]:
    """Return current external tools list (proxy tools).

    Uses DirWatcher to detect Tools/ directory changes:
    - No change → return cached (zero overhead)
    - Changed or force=True → re-scan via AST and rebuild proxies
    """
    global _cached_tools

    try:
        from backend.deepagent.dir_watcher import watcher
        changed = watcher.has_changed(_package_dir)
    except ImportError:
        changed = True

    if not changed and not force and _cached_tools:
        return _cached_tools

    with _lock:
        if not changed and not force and _cached_tools:
            return _cached_tools
        tools = _scan_and_create_proxies()
        _cached_tools = tools
        logger.info(f"[Tools] Loaded {len(tools)} proxy tools: {[t.name for t in tools]}")
        return tools


external_tools = reload_external_tools(force=True)
