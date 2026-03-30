"""
agent.py — 组装 DeepAgent：系统提示词 + 模型 + 工具（内置 + 外部扩展）+ Skills + 监控中间件。

架构：
  - HybridSandboxBackend 作为默认后端：
    - 文件操作（read_file/write_file/edit_file/ls/glob/grep）→ 本地 /home/scienceclaw/
    - 命令执行（execute）→ 远程 sandbox 容器
    - 通过 Docker 共享卷同步文件
  - CompositeBackend 路由：
    - /builtin-skills/ → FilesystemBackend（内置 skills，只读，始终加载）
    - /skills/         → FilteredFilesystemBackend（外置 skills，可屏蔽/删除）
  - deepagents 内置工具层统一管理所有工具（不再使用 MCP sandbox 工具）

Skills 架构：
  - 内置 skills（/app/builtin_skills/）：find-skills 等核心能力，
    COPY 进 Docker 镜像，不依赖宿主机挂载（避免 macOS 大小写不敏感文件系统的冲突）
  - 外置 skills（/app/Skills/）：用户通过 find-skills 下载或自行安装的 skills，
    支持屏蔽和删除管理

监控中间件：
  - SSEMonitoringMiddleware 通过 wrap_tool_call 拦截工具执行前后
  - 事件存储在 middleware.sse_events，由 runner.py 轮询消费
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend
from deepagents.middleware.subagents import GENERAL_PURPOSE_SUBAGENT, DEFAULT_SUBAGENT_PROMPT
from langchain_core.tools import StructuredTool
from backend.deepagent.engine import get_llm_model
from backend.deepagent.tools import web_search, web_crawl, propose_skill_save, propose_tool_save, eval_skill, grade_eval
from backend.deepagent.tooluniverse_tools import (
    tooluniverse_search,
    tooluniverse_info,
    tooluniverse_run,
)
from backend.deepagent.full_sandbox_backend import FullSandboxBackend
from backend.deepagent.filtered_backend import FilteredFilesystemBackend
from backend.deepagent.sse_middleware import SSEMonitoringMiddleware
from backend.deepagent.offload_middleware import ToolResultOffloadMiddleware
from backend.deepagent.diagnostic import DIAGNOSTIC_ENABLED, DiagnosticLogger
from backend.deepagent.dir_watcher import watcher as _dir_watcher
from backend.config import settings

# ───────────────────────────────────────────────────────────────────
# 外部扩展工具（Tools 目录自动扫描，支持热加载）
# ───────────────────────────────────────────────────────────────────
try:
    from Tools import reload_external_tools
    _initial = reload_external_tools(force=True)
    logger.info(f"[Agent] 已加载 {len(_initial)} 个外部扩展工具: "
                f"{[t.name for t in _initial]}")
    # Register proxy tools in SSE protocol so tool_meta carries sandbox: true
    from backend.deepagent.sse_protocol import get_protocol_manager as _get_proto
    _proto = _get_proto()
    for _t in _initial:
        _proto.register_sandbox_tool(_t.name, _t.description[:80])
    logger.info(f"[Agent] 已注册 {len(_initial)} 个沙箱代理工具到 SSE 协议")
except ImportError:
    reload_external_tools = None  # type: ignore[assignment]
    logger.warning("[Agent] 未找到 Tools 包，跳过外部扩展工具加载")

# ───────────────────────────────────────────────────────────────────
# 路径配置
# ───────────────────────────────────────────────────────────────────

_BUILTIN_SKILLS_DIR = os.environ.get("BUILTIN_SKILLS_DIR", "/app/builtin_skills")
_EXTERNAL_SKILLS_DIR = os.environ.get("EXTERNAL_SKILLS_DIR", "/app/Skills")
_BUILTIN_SKILLS_ROUTE = "/builtin-skills/"
_EXTERNAL_SKILLS_ROUTE = "/skills/"
_WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/home/scienceclaw")
_OBSIDIAN_VAULT_TOOL_NAMES = {
    "obsidian_write_materials_note",
    "obsidian_import_zotero_bbt_json",
    "obsidian_run_zotero_review_agent",
    "obsidian_rewrite_materials_review_note",
}

# ───────────────────────────────────────────────────────────────────
# Backend 构建
# ───────────────────────────────────────────────────────────────────


def _build_backend(session_id: str, sandbox: FullSandboxBackend, blocked_skills: Set[str] | None = None):
    """
    构建 CompositeBackend 工厂函数（会话级隔离）：
      - 默认: 传入的 FullSandboxBackend 实例
      - /builtin-skills/ 路由: FilesystemBackend（内置 skills，始终加载）
      - /skills/          路由: FilteredFilesystemBackend（外置 skills，过滤屏蔽项）
    """
    routes = {}

    if os.path.isdir(_BUILTIN_SKILLS_DIR):
        logger.info(f"[Skills] 内置 skills: {_BUILTIN_SKILLS_DIR} → {_BUILTIN_SKILLS_ROUTE}")
        routes[_BUILTIN_SKILLS_ROUTE] = FilesystemBackend(
            root_dir=_BUILTIN_SKILLS_DIR,
            virtual_mode=True,
        )

    if os.path.isdir(_EXTERNAL_SKILLS_DIR):
        logger.info(f"[Skills] 外置 skills: {_EXTERNAL_SKILLS_DIR} → {_EXTERNAL_SKILLS_ROUTE}"
                     f" (blocked: {blocked_skills or set()})")
        routes[_EXTERNAL_SKILLS_ROUTE] = FilteredFilesystemBackend(
            root_dir=_EXTERNAL_SKILLS_DIR,
            virtual_mode=True,
            blocked_skills=blocked_skills or set(),
        )

    if routes:
        # 返回工厂函数以确保路由生效
        return lambda rt: CompositeBackend(default=sandbox, routes=routes)
    else:
        return sandbox


# ───────────────────────────────────────────────────────────────────
# 系统提示词
# ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_TEMPLATE = """You are ScienceClaw, a proactive personal AI assistant designed to help users solve problems, conduct research, and complete tasks efficiently.

Current date and time: {current_datetime}.

## Language
Always respond in {language_instruction}.

## Core Principles
- Adapt to the conversation. Chat naturally for casual topics, but take concrete actions when the user asks for tasks or problem-solving.
- Prefer execution over explanation. If a task can be solved through code or tools, implement and execute the solution instead of only describing it.
- **File deliverables must be real files**: if the user asks for a PDF, DOCX, spreadsheet, Markdown file, or other concrete file output, you must actually create that file in the workspace. Copying a template, drafting sections, or describing the result is not sufficient.
- **Real-time information**: For any question involving current or up-to-date information, you MUST use `web_search` — NEVER answer from training data alone.
- **Write files, not chat**: When the user asks to write, create, or generate code/scripts/files, ALWAYS use `write_file` to create real files — never just paste code in chat.
- **Write → Execute → Fix loop**: After writing ANY executable script, you MUST immediately run it via `execute` to verify correctness. If it fails, fix and re-run.
- **Skill-first approach**: ALWAYS check available skills (`/builtin-skills/` and `/skills/`) before starting any task. If a skill matches, `read_file` its SKILL.md and follow the workflow. Do NOT reinvent what a skill already provides.
- **Research tasks**: When the user's request involves research, reports, reviews, surveys, literature analysis, discoveries, or any deep investigation topic, ALWAYS check and consider `/skills/deep-research/SKILL.md` first.
- **Attachment-first execution**: When the user uploads a file and asks you to use it, treat that uploaded file as the primary source of truth and prefer existing tools that operate on it directly over writing ad hoc parsers.
- **SKILL.md files are instruction documents** — use `read_file` to read them, NEVER `execute` them as scripts.
- Solve problems proactively. Only ask questions when the intent or requirements are truly unclear.

## Workspace
Your workspace directory is {workspace_dir}/.
- All files should be created under this directory using absolute paths.
- The workspace is shared between the file system and the execution sandbox.

## Obsidian Preference
{obsidian_vault_instruction}
- Whenever an Obsidian materials tool returns `effective_vault_dir`, include that actual path in your user-facing summary.
- If the tool returns `vault_match_status=normalized_same_path`, treat the configured path as successfully matched and do not describe it as a fallback.
- If the tool returns `fell_back_to_default_vault=true` or `vault_match_status=fallback_other_path`, explicitly say the configured path was not used and the write to the requested vault failed.

## Attachment Workflows
- Uploaded attachments arrive as absolute workspace paths in the user's query. Read or pass those paths directly.
- If an uploaded `.json` file appears to be a Zotero / Better BibTeX export and the user wants an end-to-end Chinese review, full-text synthesis, or Obsidian review note, prefer `obsidian_run_zotero_review_agent`.
- If the user asks to continue editing an existing review note, rewrite it into a more academic style, change citation style, or further polish a previously generated Zotero/Obsidian review, prefer `obsidian_rewrite_materials_review_note`.
- If the user only wants literature-note import or only wants a scaffold review note, prefer `obsidian_import_zotero_bbt_json` instead of writing a custom importer.
- For that workflow, infer `topic` from the user's message first, otherwise from the filename stem, and pass `vault_dir` when available.
- After import, tell the user what was created and where it was written, using the tool's `effective_vault_dir` field rather than guessing.
- For Zotero/Obsidian review generation or rewrite workflows, you MUST read these five local skills in order before the final write step:
  1. `/skills/zotero-materials-review/SKILL.md`
  2. `/skills/literature-review/SKILL.md`
  3. `/skills/scientific-writing/SKILL.md`
  4. `/skills/obsidian-markdown/SKILL.md`
  5. `/skills/materials-obsidian/SKILL.md`
- Do not skip those local skills just because you think you already know the workflow. If a required local skill is missing or unread, read it before the final write step.
- For the Zotero Review Agent workflow, use this exact task structure in `write_todos`: `校验输入`、`构建证据包`、`导入文献笔记`、`生成中文综述`、`写作润色`、`写入 Obsidian`.
- After `obsidian_run_zotero_review_agent` returns, read its `review_input_path` and `review_draft_path` when available, refine the draft into polished Chinese prose, then overwrite the same review note via `obsidian_write_materials_note` rather than creating a second manuscript note.
- When `obsidian_rewrite_materials_review_note` is appropriate, use the session's most recent successful review-note context when the user does not explicitly provide a path, and overwrite the same review note by default unless the user explicitly asks for a separate copy.
- If you already asked for overwrite confirmation and the user replies with a short affirmative such as `继续`、`开始`、`确认`、`好`、`同意` or `yes`, treat that as approval to overwrite the existing note. Do not ask for the same confirmation twice.

## Sandbox Boundary
The sandbox is an isolated execution environment. Scripts running in the sandbox CANNOT import or call your tools directly (`from functions import ...` will FAIL with `ModuleNotFoundError`).

**Data flow**: Use YOUR tools (web_search, web_crawl, tooluniverse_run, etc.) to gather data → save results to workspace files via `write_file` → write sandbox scripts that READ those files. NEVER call your tools from within sandbox scripts.

**Large tool results** are automatically saved to `research_data/` files (raw format). To use them in sandbox scripts: `read_file` the data → write a clean JSON file via a Python script with `json.dump()` → sandbox scripts read that clean file.

## Task Completion Strategy

### Step 1: Understand & Plan
- Identify ALL deliverables, requirements, and output format.
- For any task involving 2+ steps, call `write_todos` BEFORE starting.
- Check Memory: **AGENTS.md** and **CONTEXT.md**.
- **Check Available Skills (MANDATORY)** — review the skills catalog. If ANY skill matches the task, `read_file` that SKILL.md and follow its workflow. Do NOT skip this step.

### Step 2: Execute
- If a skill matched → follow the skill's workflow completely.
- Otherwise, use tools directly. Priority: existing skills > built-in tools > ToolUniverse > web_search.
- **Before `propose_tool_save`**: read `/builtin-skills/tool-creator/SKILL.md` first.
- **Before `propose_skill_save`**: read `/builtin-skills/skill-creator/SKILL.md` first.
- Build incrementally — one component per tool call. Test via `execute` after writing.

### Step 3: Verify & Deliver
- Re-read the user's original request. Check all deliverables are produced.
- If the user requested a file deliverable (for example PDF, DOCX, XLSX, or Markdown), verify that the final file exists at the expected path before finishing.
- If a script fails, fix the specific error — do NOT rewrite from scratch. If it fails 2+ times, simplify.

### Step 4: Reflect & Capture
After completing a non-trivial task:
- **Reusable workflow** → Suggest saving as a **skill** via skill-creator.
- **Reusable function** → Suggest saving as a **tool** via tool-creator.
- **User preference learned** → Update **AGENTS.md** via `edit_file`.
- **Project context learned** → Update **CONTEXT.md** via `edit_file`.
"""


_EVAL_SYSTEM_PROMPT_TEMPLATE = """You are ScienceClaw, a proactive personal AI assistant designed to help users solve problems, conduct research, and complete tasks efficiently.

Current date and time: {current_datetime}

## Core Principles
- Prefer execution over explanation. If a task can be solved through code or tools, implement and execute the solution instead of only describing it.
- Always respond in the same language the user uses.
- When the user asks to write, create, or generate code/scripts/files, ALWAYS use write_file to create real files.
- Use sandbox execution whenever it can produce verifiable results.

## Workspace
Your workspace directory is {workspace_dir}/.
- All files should be created under this directory using absolute paths.
- The workspace is shared between the file system and the execution sandbox.
"""


_LANGUAGE_MAP = {
    "zh": ("Chinese (Simplified)", "你必须使用简体中文回复所有内容。所有生成的报告、文档标题和正文也必须使用简体中文。"),
    "en": ("English", "You must respond in English. All generated reports, document titles and body text must also be in English."),
}


def get_system_prompt(
    workspace_dir: str,
    sandbox_env: str | None = None,
    language: str | None = None,
    obsidian_vault_dir: str | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    lang_code = (language or "").strip().lower()
    if lang_code in _LANGUAGE_MAP:
        lang_name, lang_detail = _LANGUAGE_MAP[lang_code]
        language_instruction = (
            f"- The user has set their preferred language to **{lang_name}** (code: `{lang_code}`).\n"
            f"- {lang_detail}\n"
            f"- This applies to ALL outputs: conversation replies, report content, section titles, chart labels, and file names."
        )
    else:
        language_instruction = "- Always respond in the same language the user uses."

    preferred_vault = (obsidian_vault_dir or "").strip()
    if preferred_vault:
        obsidian_vault_instruction = (
            f"- The user configured a preferred Obsidian vault path: `{preferred_vault}`.\n"
            f"- When calling `obsidian_write_materials_note` or `obsidian_import_zotero_bbt_json`, pass this value as `vault_dir` when possible.\n"
            f"- Treat that configured vault path as strict: if the runtime cannot write to that path through the host bridge, the task should fail instead of silently falling back to `/home/scienceclaw/obsidian_vault`."
        )
    else:
        obsidian_vault_instruction = (
            "- No user-specific Obsidian vault path is configured.\n"
            "- Use the mounted/default vault path when calling Obsidian materials tools."
        )

    prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        current_datetime=now,
        workspace_dir=workspace_dir,
        language_instruction=language_instruction,
        obsidian_vault_instruction=obsidian_vault_instruction,
    )
    if sandbox_env:
        prompt += f"\n\n## Sandbox Environment Information\n{sandbox_env}"
    return prompt


def _get_eval_system_prompt(workspace_dir: str, sandbox_env: str | None = None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    prompt = _EVAL_SYSTEM_PROMPT_TEMPLATE.format(
        current_datetime=now,
        workspace_dir=workspace_dir,
    )
    if sandbox_env:
        prompt += f"\n\n## Sandbox Environment Information\n{sandbox_env}"
    return prompt


# ───────────────────────────────────────────────────────────────────
# 工具列表（内置 + 外部扩展，不再包含 MCP sandbox 工具）
# ───────────────────────────────────────────────────────────────────

_STATIC_TOOLS = [
    web_search, web_crawl, propose_skill_save, propose_tool_save,
    eval_skill, grade_eval,
    tooluniverse_search, tooluniverse_info, tooluniverse_run,
]


def _inject_default_vault_dir(tool_obj: Any, preferred_vault: str) -> Any:
    preferred = (preferred_vault or "").strip()
    if not preferred:
        return tool_obj
    if getattr(tool_obj, "name", "") not in _OBSIDIAN_VAULT_TOOL_NAMES:
        return tool_obj
    if not isinstance(tool_obj, StructuredTool):
        return tool_obj

    base_func = getattr(tool_obj, "func", None)
    if base_func is None:
        return tool_obj

    def _wrapped_func(*args: Any, **kwargs: Any) -> Any:
        actual_kwargs = dict(kwargs)
        if not str(actual_kwargs.get("vault_dir", "") or "").strip():
            actual_kwargs["vault_dir"] = preferred
        return base_func(*args, **actual_kwargs)

    updates: Dict[str, Any] = {"func": _wrapped_func}
    base_coroutine = getattr(tool_obj, "coroutine", None)
    if base_coroutine is not None:
        async def _wrapped_coroutine(*args: Any, **kwargs: Any) -> Any:
            actual_kwargs = dict(kwargs)
            if not str(actual_kwargs.get("vault_dir", "") or "").strip():
                actual_kwargs["vault_dir"] = preferred
            return await base_coroutine(*args, **actual_kwargs)

        updates["coroutine"] = _wrapped_coroutine

    logger.info(f"[Agent] Injecting preferred Obsidian vault into tool {tool_obj.name}: {preferred}")
    return tool_obj.model_copy(update=updates)


def _collect_tools(blocked_tools: Set[str] | None = None, preferred_vault: str = "") -> List:
    """合并内置工具与外部扩展工具，去重并过滤屏蔽项。

    通过 DirWatcher 检测 Tools/ 目录变更，仅在变更时才重新 import 模块。
    """
    blocked = blocked_tools or set()
    seen_names: set[str] = set()
    all_tools: List = []

    ext_tools: list = []
    if reload_external_tools is not None:
        try:
            ext_tools = reload_external_tools()
        except Exception:
            logger.warning("[Agent] 动态加载外部工具失败", exc_info=True)

    for t in _STATIC_TOOLS + ext_tools:
        if t.name in blocked:
            logger.info(f"[Agent] 工具已屏蔽，跳过: {t.name}")
            continue
        t = _inject_default_vault_dir(t, preferred_vault)
        if t.name not in seen_names:
            all_tools.append(t)
            seen_names.add(t.name)
        else:
            logger.warning(f"[Agent] 工具名称重复，跳过: {t.name}")
    logger.info(f"[Agent] 自定义工具列表({len(all_tools)}): {[t.name for t in all_tools]}")
    return all_tools


# ───────────────────────────────────────────────────────────────────
# 屏蔽查询（MongoDB）
# ───────────────────────────────────────────────────────────────────

async def get_blocked_skills(user_id: str) -> Set[str]:
    """从 MongoDB 查询用户屏蔽的 skills 列表。"""
    try:
        from backend.mongodb.db import db
        col = db.get_collection("blocked_skills")
        cursor = col.find({"user_id": user_id}, {"skill_name": 1})
        blocked = set()
        async for doc in cursor:
            name = doc.get("skill_name")
            if name:
                blocked.add(name)
        return blocked
    except Exception as exc:
        logger.warning(f"[Skills] 查询屏蔽列表失败: {exc}")
        return set()


async def get_blocked_tools(user_id: str) -> Set[str]:
    """从 MongoDB 查询用户屏蔽的 tools 列表。"""
    try:
        from backend.mongodb.db import db
        col = db.get_collection("blocked_tools")
        cursor = col.find({"user_id": user_id}, {"tool_name": 1})
        blocked = set()
        async for doc in cursor:
            name = doc.get("tool_name")
            if name:
                blocked.add(name)
        return blocked
    except Exception as exc:
        logger.warning(f"[Tools] 查询屏蔽列表失败: {exc}")
        return set()


# ───────────────────────────────────────────────────────────────────
# 创建 Agent
# ───────────────────────────────────────────────────────────────────

async def deep_agent(
    session_id: str,
    model_config: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    task_settings: Optional["TaskSettings"] = None,
    diagnostic_enabled: bool = False,
    language: Optional[str] = None,
) -> Tuple[Any, SSEMonitoringMiddleware, int, Optional[DiagnosticLogger]]:
    """
    创建一个完整的 DeepAgent 实例（会话级隔离），并注入 SSE 监控中间件。

    Returns:
        (agent, sse_middleware, context_window, diagnostic_logger)

    Skills 架构：
      - 内置 skills（/app/builtin_skills/）：COPY 进镜像，始终加载
      - 外置 skills（/app/Skills/）：用户自管理，支持屏蔽过滤
    """
    from backend.task_settings import TaskSettings as _TS
    ts: _TS = task_settings or _TS()
    model = get_llm_model(model_config, max_tokens_override=ts.max_tokens)
    context_window = getattr(model, "profile", {}).get("max_input_tokens", 131_072)

    blocked_skills = set()
    blocked_tools = set()
    if user_id:
        blocked_skills = await get_blocked_skills(user_id)
        blocked_tools = await get_blocked_tools(user_id)

    # ── 检测 Tools/Skills 目录变更并按需重新加载 ──
    _dir_watcher.has_changed(_EXTERNAL_SKILLS_DIR)

    tools = _collect_tools(blocked_tools=blocked_tools, preferred_vault=ts.obsidian_vault_dir)

    sse_middleware = SSEMonitoringMiddleware(
        agent_name="DeepAgent",
        parent_agent=None,
        verbose=False,
    )

    # 1. 实例化 FullSandboxBackend 并获取环境上下文
    sandbox = FullSandboxBackend(
        session_id=session_id,
        user_id=user_id or "default_user",
        base_dir=_WORKSPACE_DIR,
        execute_timeout=ts.sandbox_exec_timeout,
        max_output_chars=ts.max_output_chars,
    )
    
    sandbox_info = None
    actual_workspace = sandbox.workspace  # /home/scienceclaw/{session_id}（与后端共享卷）
    
    ctx = await sandbox.get_context()
    if ctx.get("success"):
        sandbox_info = ctx.get("data")

    # 2. 构建复合后端（可能包含 Skills 路由）
    backend = _build_backend(session_id, sandbox, blocked_skills=blocked_skills)

    # 工具结果自动落盘中间件：大型工具结果写入文件，Agent 按需 read_file 读取
    offload_middleware = ToolResultOffloadMiddleware(
        workspace_dir=actual_workspace,
        backend=sandbox,
    )

    # ── 诊断模式：记录 LLM 每步看到的完整上下文 ──
    diag: Optional[DiagnosticLogger] = None
    if diagnostic_enabled:
        diag = DiagnosticLogger(actual_workspace, session_id)
        offload_middleware._diagnostic = diag

    # 中间件执行顺序：offload（修改结果）→ SSE（监控记录）
    # create_deep_agent 还会自动注入 SummarizationMiddleware（基于 model profile）
    agent_kwargs: Dict[str, Any] = {
        "model": model,
        "tools": tools,
        "middleware": [offload_middleware, sse_middleware],
    }

    # 4. 注入系统提示词
    system_prompt = get_system_prompt(
        actual_workspace,
        sandbox_info,
        language=language,
        obsidian_vault_dir=ts.obsidian_vault_dir,
    )
    agent_kwargs["system_prompt"] = system_prompt

    if diag:
        diag.save_system_prompt(system_prompt)

    agent_kwargs["backend"] = backend

    skills_sources: List[str] = []
    if os.path.isdir(_BUILTIN_SKILLS_DIR):
        skills_sources.append(_BUILTIN_SKILLS_ROUTE)
    if os.path.isdir(_EXTERNAL_SKILLS_DIR):
        skills_sources.append(_EXTERNAL_SKILLS_ROUTE)

    if skills_sources:
        agent_kwargs["skills"] = skills_sources
        logger.info(f"[Agent] 已启用 Skills（sources: {skills_sources}, blocked: {blocked_skills}）")

    # 4. 启用跨会话记忆（两层隔离）
    #    - 全局 AGENTS.md：用户偏好 + 通用模式（跨所有会话，体量小）
    #    - 会话级 CONTEXT.md：当前项目/任务上下文（会话删除时自动清理）
    _mem_user = user_id or "default_user"
    _mem_dir = os.path.join(_WORKSPACE_DIR, "_memory", _mem_user)
    os.makedirs(_mem_dir, exist_ok=True)
    os.chmod(_mem_dir, 0o777)
    _global_mem = os.path.join(_mem_dir, "AGENTS.md")
    if not os.path.isfile(_global_mem):
        with open(_global_mem, "w") as f:
            f.write("# Global Memory (persists across all sessions)\n\n"
                    "## User Preferences\n\n"
                    "## General Patterns\n\n"
                    "## Notes\n")
        logger.info(f"[Memory] 初始化全局 Memory: {_global_mem}")

    _session_mem = os.path.join(actual_workspace, "CONTEXT.md")
    if not os.path.isfile(_session_mem):
        with open(_session_mem, "w") as f:
            f.write("# Session Context (this session only)\n\n"
                    "## Project Context\n\n"
                    "## Task Notes\n")
        logger.info(f"[Memory] 初始化会话 Context: {_session_mem}")

    _MAX_MEMORY_CHARS = 4000
    _mem_files_to_use = []
    for _mf in [_global_mem, _session_mem]:
        try:
            _mf_size = os.path.getsize(_mf)
            if _mf_size > _MAX_MEMORY_CHARS:
                with open(_mf, "r", encoding="utf-8") as f:
                    _full = f.read()
                _truncated = _full[:_MAX_MEMORY_CHARS].rsplit("\n", 1)[0]
                _tmp_path = _mf + ".truncated"
                with open(_tmp_path, "w", encoding="utf-8") as f:
                    f.write(_truncated + "\n\n(Memory truncated — keep entries concise to stay under limit)\n")
                _mem_files_to_use.append(_tmp_path)
                logger.warning(
                    f"[Memory] {os.path.basename(_mf)} too large ({_mf_size:,} chars), "
                    f"truncated to {_MAX_MEMORY_CHARS:,} for injection"
                )
            else:
                _mem_files_to_use.append(_mf)
        except Exception:
            _mem_files_to_use.append(_mf)

    agent_kwargs["memory"] = _mem_files_to_use
    logger.info(f"[Memory] 已启用记忆: {[os.path.basename(f) for f in _mem_files_to_use]}")

    # 将主 agent 的关键策略注入到 general-purpose 子 agent 的 system_prompt，
    # 使子 agent 在处理 skill/tool 相关任务时遵循相同的工作流。
    _subagent_policy = f"""\n
## Workspace
Your workspace directory is {actual_workspace}/.
All files should be created under this directory using absolute paths.
SKILL.md files are instruction documents — use `read_file` to read them, NEVER `execute` them.

## Skills CLI (CRITICAL)
NEVER use `npx skills`. Use `skills` directly. When installing: `HOME={actual_workspace} skills add <package> -g -y --agent '*'`. ALL flags are mandatory — omitting any will hang on interactive prompts.

## Task Resources
- **Existing skill?** → `read_file` the SKILL.md and follow it. Check `/skills/` for local installs first.
- **Research / reports / reviews / surveys / discoveries?** → `read_file("/skills/deep-research/SKILL.md")` and follow its workflow.
- **Need a capability?** → Check built-in tools, then `read_file("/builtin-skills/tooluniverse/SKILL.md")`.
- **PDF processing?** → `read_file("/builtin-skills/pdf/SKILL.md")`. For form filling, also read FORMS.md.
- **Need external info?** → `web_search` / `web_crawl`.
- **Create a tool** → `read_file("/builtin-skills/tool-creator/SKILL.md")`. NEVER write to /app/Tools/ directly.
- **Create a skill** → `read_file("/builtin-skills/skill-creator/SKILL.md")`. NEVER write to `/skills/` directly.
- **Find ecosystem skill** → `read_file("/builtin-skills/find-skills/SKILL.md")`. After 2-3 failures, create from scratch.
Always use `write_file` to workspace then `propose_skill_save` / `propose_tool_save`.
"""
    GENERAL_PURPOSE_SUBAGENT["system_prompt"] = DEFAULT_SUBAGENT_PROMPT + _subagent_policy

    agent = create_deep_agent(**agent_kwargs)

    GENERAL_PURPOSE_SUBAGENT["system_prompt"] = DEFAULT_SUBAGENT_PROMPT

    logger.info(
        f"[Agent] session={session_id}, workspace={actual_workspace}, "
        f"middleware={sse_middleware.agent_name}, context_window={context_window:,}"
        f"{', diagnostic=ON' if diag else ''}"
    )
    return agent, sse_middleware, context_window, diag


# ───────────────────────────────────────────────────────────────────
# Eval 模式 Agent（精简版，用于 skill 测试）
# ───────────────────────────────────────────────────────────────────

async def deep_agent_eval(
    session_id: str,
    model_config: Optional[Dict[str, Any]] = None,
    skill_sources: Optional[List[str]] = None,
) -> Tuple[Any, SSEMonitoringMiddleware]:
    """
    创建用于 eval 测试的精简 Agent — 不含元工具，只加载目标 skill。

    与 deep_agent() 的关键差异：
      - 精简 system prompt（无 skill-creator/tool-creator 指令）
      - 不包含 propose_skill_save / propose_tool_save 等元工具
      - 不加载外部扩展工具（Tools/）
      - 可指定只加载特定 skill sources
    """
    from backend.task_settings import TaskSettings as _TS
    ts = _TS()
    model = get_llm_model(model_config, max_tokens_override=ts.max_tokens)

    eval_tools = [web_search, web_crawl]

    middleware = SSEMonitoringMiddleware(
        agent_name="EvalAgent",
        parent_agent=None,
        verbose=False,
    )

    sandbox = FullSandboxBackend(
        session_id=session_id,
        user_id="eval_runner",
        base_dir=_WORKSPACE_DIR,
        execute_timeout=ts.sandbox_exec_timeout,
        max_output_chars=ts.max_output_chars,
    )

    actual_workspace = sandbox.workspace
    sandbox_info = None
    ctx = await sandbox.get_context()
    if ctx.get("success"):
        sandbox_info = ctx.get("data")

    system_prompt = _get_eval_system_prompt(actual_workspace, sandbox_info)

    agent_kwargs: Dict[str, Any] = {
        "model": model,
        "tools": eval_tools,
        "middleware": [middleware],
        "system_prompt": system_prompt,
    }

    # 构建后端（含 skill 路由）
    routes = {}
    resolved_sources: List[str] = []

    if skill_sources:
        for src in skill_sources:
            if src == _BUILTIN_SKILLS_ROUTE and os.path.isdir(_BUILTIN_SKILLS_DIR):
                routes[_BUILTIN_SKILLS_ROUTE] = FilesystemBackend(
                    root_dir=_BUILTIN_SKILLS_DIR, virtual_mode=True,
                )
                resolved_sources.append(_BUILTIN_SKILLS_ROUTE)
            elif src == _EXTERNAL_SKILLS_ROUTE and os.path.isdir(_EXTERNAL_SKILLS_DIR):
                routes[_EXTERNAL_SKILLS_ROUTE] = FilteredFilesystemBackend(
                    root_dir=_EXTERNAL_SKILLS_DIR, virtual_mode=True,
                    blocked_skills=set(),
                )
                resolved_sources.append(_EXTERNAL_SKILLS_ROUTE)
    else:
        if os.path.isdir(_EXTERNAL_SKILLS_DIR):
            routes[_EXTERNAL_SKILLS_ROUTE] = FilteredFilesystemBackend(
                root_dir=_EXTERNAL_SKILLS_DIR, virtual_mode=True,
                blocked_skills=set(),
            )
            resolved_sources.append(_EXTERNAL_SKILLS_ROUTE)

    if routes:
        agent_kwargs["backend"] = lambda rt: CompositeBackend(default=sandbox, routes=routes)
    else:
        agent_kwargs["backend"] = sandbox

    if resolved_sources:
        agent_kwargs["skills"] = resolved_sources

    agent = create_deep_agent(**agent_kwargs)
    logger.info(f"[EvalAgent] session={session_id}, workspace={actual_workspace}, skills={resolved_sources}")
    return agent, middleware
