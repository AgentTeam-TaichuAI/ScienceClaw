import importlib.util
import json
import logging
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Obsidian",
    "subcategory": "Review Agent",
    "tags": ["obsidian", "zotero", "review", "agent", "better-bibtex"],
}

_SKIP_ITEM_TYPES = {"attachment", "note"}
_TOOL_CACHE: dict[str, Any] = {}
_REQUIRED_LOCAL_SKILLS = [
    "zotero-materials-review",
    "literature-review",
    "scientific-writing",
    "obsidian-markdown",
    "materials-obsidian",
]
_REVIEW_SECTION_HEADINGS = [
    "## 摘要",
    "## 关键词",
    "## 引言",
    "## 主要研究方向",
    "## 代表性工作比较与讨论",
    "## 挑战与争议",
    "## 未来趋势与机会",
    "## 结论",
    "## 参考文献",
]


def _slugify_category(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", str(value or ""), flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", cleaned).strip("-_").lower()


def _normalize_category(value: str, topic: str) -> str:
    explicit = str(value or "").strip()
    topic_text = str(topic or "").strip()
    if not explicit:
        return topic_text
    explicit_slug = _slugify_category(explicit)
    topic_slug = _slugify_category(topic_text)
    if explicit_slug in {"material", "materials"} and topic_slug and explicit_slug != topic_slug:
        return topic_text
    return explicit


def _load_tool(filename: str, attr_name: str):
    cache_key = f"{filename}:{attr_name}"
    cached = _TOOL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    tool_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"scienceclaw_{tool_path.stem}_module", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load tool from {tool_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool_obj = getattr(module, attr_name, None)
    if tool_obj is None or not hasattr(tool_obj, "invoke"):
        raise RuntimeError(f"Tool {attr_name} is unavailable in {tool_path}")

    _TOOL_CACHE[cache_key] = tool_obj
    return tool_obj


def _load_bundle_tool():
    return _load_tool("obsidian_build_zotero_review_bundle.py", "obsidian_build_zotero_review_bundle")


def _load_import_tool():
    return _load_tool("obsidian_import_zotero_bbt_json.py", "obsidian_import_zotero_bbt_json")


def _load_writer_tool():
    return _load_tool("obsidian_write_materials_note.py", "obsidian_write_materials_note")


def _backend_root_candidates() -> list[Path]:
    return [
        Path(__file__).resolve().parent.parent / "ScienceClaw",
        Path("/app/ScienceClaw"),
        Path("/app"),
        Path.cwd() / "ScienceClaw",
        Path.cwd(),
    ]


def _resolve_backend_root() -> Path | None:
    for candidate in _backend_root_candidates():
        if (candidate / "backend").exists():
            return candidate
    return None


def _load_llm_model():
    backend_root = _resolve_backend_root()
    if backend_root is None:
        raise RuntimeError("Unable to locate ScienceClaw backend package for review-agent LLM loading")
    backend_root_str = str(backend_root)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)
    from backend.config import settings
    from backend.deepagent.engine import get_llm_model

    config: dict[str, Any] | None = None
    if not getattr(settings, "model_ds_api_key", ""):
        config = _load_llm_config_from_mongo()
    return get_llm_model(config=config, streaming=False)


def _load_llm_config_from_mongo() -> dict[str, Any] | None:
    try:
        backend_root = _resolve_backend_root()
        if backend_root is None:
            raise RuntimeError("backend package not available")
        backend_root_str = str(backend_root)
        if backend_root_str not in sys.path:
            sys.path.insert(0, backend_root_str)
        from backend.config import settings
        from pymongo import MongoClient
    except Exception as exc:
        logger.warning("[obsidian_run_zotero_review_agent] unable to import Mongo-backed model config helpers: %s", exc)
        return None

    mongo_client = None
    try:
        mongo_client = MongoClient(
            host=getattr(settings, "mongodb_host", "localhost"),
            port=int(getattr(settings, "mongodb_port", 27017)),
            username=getattr(settings, "mongodb_username", "") or None,
            password=getattr(settings, "mongodb_password", "") or None,
            serverSelectionTimeoutMS=3000,
        )
        database = mongo_client[getattr(settings, "mongodb_db_name", "ai_agent")]

        session_doc = database["sessions"].find_one(
            {"model_config.api_key": {"$exists": True, "$nin": ["", None]}},
            sort=[("updated_at", -1)],
            projection={"model_config": 1},
        )
        session_config = (session_doc or {}).get("model_config")
        if isinstance(session_config, dict) and str(session_config.get("api_key", "")).strip():
            return {
                "model_name": session_config.get("model_name"),
                "base_url": session_config.get("base_url"),
                "api_key": session_config.get("api_key"),
                "context_window": session_config.get("context_window"),
            }

        model_doc = database["models"].find_one(
            {"api_key": {"$exists": True, "$nin": ["", None]}, "is_active": True},
            sort=[("updated_at", -1)],
            projection={"model_name": 1, "base_url": 1, "api_key": 1, "context_window": 1},
        )
        if isinstance(model_doc, dict) and str(model_doc.get("api_key", "")).strip():
            return {
                "model_name": model_doc.get("model_name"),
                "base_url": model_doc.get("base_url"),
                "api_key": model_doc.get("api_key"),
                "context_window": model_doc.get("context_window"),
            }
    except Exception as exc:
        logger.warning("[obsidian_run_zotero_review_agent] failed to resolve tool LLM config from Mongo: %s", exc)
    finally:
        if mongo_client is not None:
            mongo_client.close()
    return None


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = text.replace("\x00", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", _clean_text(text)).strip()


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _safe_slug(value: str, fallback: str = "review-agent") -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", str(value or ""), flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-_")
    return slug or fallback


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(part for part in parts if part).strip()
    return str(content or "")


def _strip_markdown_fence(text: str) -> str:
    stripped = str(text or "").strip()
    match = re.match(r"^```(?:markdown|md)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return stripped


def _truncate_text(value: Any, limit: int = 320) -> str:
    text = _normalize_whitespace(str(value or ""))
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rstrip(" ,;:，；：")
    return clipped + "…"


def _truncate_block_text(value: Any, limit: int = 4000) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _normalize_authors(value: Any) -> str:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return "；".join(items)
    return _truncate_text(value, limit=180)


def _skills_root() -> Path:
    for candidate in _skill_root_candidates():
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent.parent / "Skills"


def _skill_root_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("EXTERNAL_SKILLS_DIR", "SKILLS_DIR"):
        raw = str(os.environ.get(env_name, "")).strip()
        if raw:
            candidates.append(Path(raw))
    candidates.extend(
        [
            Path(__file__).resolve().parent.parent / "Skills",
            Path("/app/Skills"),
            Path("/skills"),
            Path.cwd() / "Skills",
        ]
    )
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        raw = str(candidate).strip()
        if not raw:
            continue
        key = candidate.as_posix() if candidate.is_absolute() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _find_skill_doc(skill_name: str) -> Path | None:
    for root in _skill_root_candidates():
        skill_path = root / skill_name / "SKILL.md"
        if skill_path.exists():
            return skill_path
    return None


def _read_required_skill_docs(required_skills: list[str]) -> tuple[list[dict[str, str]], list[str], list[str]]:
    docs: list[dict[str, str]] = []
    read_skills: list[str] = []
    missing_skills: list[str] = []
    for skill_name in required_skills:
        skill_path = _find_skill_doc(skill_name)
        if skill_path is None:
            missing_skills.append(skill_name)
            continue
        docs.append(
            {
                "name": skill_name,
                "path": str(skill_path),
                "content": skill_path.read_text(encoding="utf-8"),
            }
        )
        read_skills.append(skill_name)
    return docs, read_skills, missing_skills


def _summarize_page_excerpts(paper: dict[str, Any], max_items: int = 2) -> str:
    excerpts = paper.get("page_excerpts", [])
    if not isinstance(excerpts, list):
        return "无页面摘录"
    lines: list[str] = []
    for row in excerpts[:max_items]:
        if not isinstance(row, dict):
            continue
        page_label = str(row.get("page_label", "")).strip() or "未标页"
        section = str(row.get("section", "")).strip() or "evidence"
        excerpt = _truncate_text(row.get("excerpt", ""), limit=220)
        if excerpt:
            lines.append(f"{page_label} / {section}: {excerpt}")
    return " | ".join(lines) if lines else "无页面摘录"


def _paper_prompt_block(index: int, paper: dict[str, Any]) -> str:
    title = str(paper.get("title", "")).strip() or "Untitled"
    year = str(paper.get("year", "")).strip() or "n.d."
    citekey = str(paper.get("citekey", "")).strip()
    note_path = str(paper.get("relative_note_path", "")).strip()
    theme = str(paper.get("theme_label", "")).strip() or "未分组"
    relevance = str(paper.get("relevance_label", "")).strip() or "unknown"
    authors = _normalize_authors(paper.get("authors", []))
    return "\n".join(
        [
            f"{index}. {title} ({year})",
            f"   citekey: {citekey or 'n/a'}",
            f"   authors: {authors or 'n/a'}",
            f"   note: {note_path or 'n/a'}",
            f"   theme: {theme}",
            f"   relevance: {relevance}",
            f"   summary: {_truncate_text(paper.get('one_sentence_summary', ''), limit=220) or 'n/a'}",
            f"   methods: {_truncate_text(paper.get('methods_summary', ''), limit=260) or 'n/a'}",
            f"   findings: {_truncate_text(paper.get('key_findings', ''), limit=280) or 'n/a'}",
            f"   limitations: {_truncate_text(paper.get('limitations', ''), limit=220) or 'n/a'}",
            f"   page_evidence: {_summarize_page_excerpts(paper)}",
        ]
    )


def _build_evidence_brief(writing_input: dict[str, Any]) -> str:
    topic = str(writing_input.get("topic", "")).strip()
    keywords = "、".join(str(item).strip() for item in writing_input.get("keywords", []) if str(item).strip())
    warnings = writing_input.get("warnings", [])
    warning_text = "\n".join(f"- {str(item).strip()}" for item in warnings if str(item).strip()) or "- 无"
    pdf_stats = writing_input.get("pdf_stats", {}) if isinstance(writing_input.get("pdf_stats"), dict) else {}
    core_papers = writing_input.get("core_papers", []) if isinstance(writing_input.get("core_papers"), list) else []
    boundary_papers = writing_input.get("boundary_papers", []) if isinstance(writing_input.get("boundary_papers"), list) else []
    noise_papers = writing_input.get("noise_papers", []) if isinstance(writing_input.get("noise_papers"), list) else []
    section_hints = writing_input.get("section_hints", []) if isinstance(writing_input.get("section_hints"), list) else []
    section_text = "、".join(str(item).strip() for item in section_hints if str(item).strip()) or "未提供"
    lines = [
        f"主题: {topic or '未命名主题'}",
        f"关键词: {keywords or '未提供'}",
        f"纳入文献: core={len(core_papers)}, boundary={len(boundary_papers)}, noise={len(noise_papers)}",
        "PDF统计:",
        f"- total_papers={int(pdf_stats.get('total_papers', 0) or 0)}",
        f"- accessible_pdf_count={int(pdf_stats.get('accessible_pdf_count', 0) or 0)}",
        f"- fulltext_ready_count={int(pdf_stats.get('fulltext_ready_count', 0) or 0)}",
        f"- missing_pdf_count={int(pdf_stats.get('missing_pdf_count', 0) or 0)}",
        f"- metadata_conflict_count={int(pdf_stats.get('metadata_conflict_count', 0) or 0)}",
        f"section_hints: {section_text}",
        "warnings:",
        warning_text,
        "",
        "核心文献:",
    ]
    lines.extend(_paper_prompt_block(index, paper) for index, paper in enumerate(core_papers[:8], start=1))
    if boundary_papers:
        lines.extend(["", "边界文献:"])
        lines.extend(
            _paper_prompt_block(index, paper)
            for index, paper in enumerate(boundary_papers[:5], start=1)
        )
    if noise_papers:
        lines.extend(["", "排除/噪声文献:"])
        for index, paper in enumerate(noise_papers[:3], start=1):
            title = str(paper.get("title", "")).strip() or "Untitled"
            reason = str(paper.get("relevance_reason", "")).strip() or str(paper.get("relevance_label", "")).strip() or "未说明"
            lines.append(f"{index}. {title} - {reason}")
    return "\n".join(lines).strip()


def _skill_docs_block(skill_docs: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for doc in skill_docs:
        blocks.append(
            "\n".join(
                [
                    f"=== {doc['name']} ===",
                    f"path: {doc['path']}",
                    doc["content"].strip(),
                ]
            )
        )
    return "\n\n".join(blocks).strip()


def _sanitize_polished_review(topic: str, markdown: str) -> str:
    cleaned = _strip_markdown_fence(markdown).replace("\r", "\n").strip()
    cleaned = re.sub(r"(?ms)^> \[!info\].*?(?:\n\n|$)", "", cleaned).strip()
    if not re.search(r"(?m)^#\s+", cleaned):
        cleaned = f"# {topic}\n\n{cleaned}"
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def _count_present_sections(markdown: str) -> int:
    return sum(1 for heading in _REVIEW_SECTION_HEADINGS if heading in markdown)


def _polish_review_with_local_skills(
    topic: str,
    draft_markdown: str,
    writing_input: dict[str, Any],
    revision_request: str = "",
    current_body: str = "",
    review_note_path: str = "",
) -> dict[str, Any]:
    skill_docs, read_skills, missing_skills = _read_required_skill_docs(list(_REQUIRED_LOCAL_SKILLS))
    if missing_skills:
        return {
            "ok": False,
            "error": "Missing required local skills: " + ", ".join(missing_skills),
            "read_skills": read_skills,
            "missing_required_skills": missing_skills,
        }

    system_prompt = (
        "你是 ScienceClaw 的 Zotero/Obsidian 中文综述写作器。"
        "你的工作不是照抄 PDF/OCR 原文，而是严格依据本地证据进行综述性综合。"
        "你必须先遵循提供的 5 个本地 skill，再输出最终 Markdown。"
        "禁止捏造事实、引用、页码、实验结果；证据不充分时要明确写成局限。"
        "最终输出必须是适合 Obsidian 的中文综述正文，不要输出解释、前言或代码围栏。"
    )
    evidence_brief = _build_evidence_brief(writing_input)
    request_line = revision_request.strip() or "请生成第一版正式中文综述，并使其像真实文献综述而不是工具拼接稿。"
    user_prompt = "\n\n".join(
        [
            "请严格按以下顺序使用本地技能："
            "1. zotero-materials-review"
            " 2. literature-review"
            " 3. scientific-writing"
            " 4. obsidian-markdown"
            " 5. materials-obsidian",
            "本地 skill 文档如下，请把它们当作刚刚读取过的工作流说明：\n" + _skill_docs_block(skill_docs),
            f"任务主题: {topic}",
            f"当前 review note 路径: {review_note_path or str(writing_input.get('review_note_path', '')).strip() or '未提供'}",
            f"用户要求: {request_line}",
            "输出要求:\n"
            "- 只输出 Markdown 正文，不要 ```markdown 包裹。\n"
            "- 只保留一个一级标题 `# 主题`。\n"
            "- 正文必须是中文学术段落，不要逐篇论文 bullet dump。\n"
            "- 不要保留“生成说明”或 workflow callout。\n"
            "- 不要直接粘贴大段英文 PDF 原文，必须先消化后用中文综合表达。\n"
            "- `## 参考文献` 使用编号条目；若已有作者/年份/题名则尽量组织成接近 GB/T 7714 的形式，缺失字段不要杜撰。\n"
            "- 若存在 `relative_note_path`，可在参考文献条目末尾追加对应的 Obsidian wikilink 便于追溯。\n"
            "- 至少覆盖以下章节：\n  "
            + "\n  ".join(_REVIEW_SECTION_HEADINGS),
            "结构化证据摘要:\n" + evidence_brief,
            "现有草稿:\n" + _truncate_block_text(draft_markdown, limit=12000),
            "当前笔记正文（如有）:\n" + (_truncate_block_text(current_body, limit=5000) or "无"),
        ]
    )

    llm = _load_llm_model()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    last_markdown = ""
    for attempt in range(2):
        response = llm.invoke(messages)
        candidate = _sanitize_polished_review(topic, _extract_message_text(getattr(response, "content", response)))
        last_markdown = candidate
        if _count_present_sections(candidate) >= 7:
            return {
                "ok": True,
                "markdown": candidate,
                "read_skills": read_skills,
                "missing_required_skills": [],
            }
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=user_prompt
                + "\n\n你上一版输出的章节结构不完整。请完整重写，确保九个主章节齐全，并维持中文学术综述风格。"
            ),
        ]

    return {
        "ok": False,
        "error": "Skill-driven rewrite produced incomplete review structure",
        "read_skills": read_skills,
        "missing_required_skills": [],
        "markdown": last_markdown,
    }


def _validate_bbt_export(payload: Any) -> tuple[bool, str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return False, "Expected Better BibTeX export to be a JSON object", []

    items = payload.get("items", [])
    if not isinstance(items, list):
        return False, "Expected `items` to be a list in Better BibTeX export", []

    parent_items = [
        item for item in items
        if isinstance(item, dict) and str(item.get("itemType", "")).strip().lower() not in _SKIP_ITEM_TYPES
    ]
    if not parent_items:
        return False, "No parent references found in Better BibTeX export", []
    return True, "", parent_items


def _summarize_pages(row: dict[str, Any]) -> str:
    pages = row.get("pages", [])
    if not isinstance(pages, list) or not pages:
        return "未记录页码"
    if len(pages) == 1:
        return f"第 {pages[0]} 页"
    return "第 " + "、".join(str(page) for page in pages) + " 页"


def _make_page_excerpt(section: str, row: dict[str, Any], excerpt: str) -> dict[str, Any]:
    return {
        "section": section,
        "pages": row.get("pages", []) if isinstance(row.get("pages", []), list) else [],
        "page_label": _summarize_pages(row),
        "excerpt": _clean_text(excerpt),
    }


def _guess_theme_label(paper: dict[str, Any]) -> str:
    text = "\n".join(
        [
            str(paper.get("title", "")),
            str(paper.get("one_sentence_summary", "")),
            str(paper.get("methods_summary", "")),
            str(paper.get("key_findings", "")),
        ]
    ).lower()

    if any(token in text for token in ("agent", "workflow", "assistant", "copilot", "autonomous")):
        return "智能代理与科研工作流"
    if any(token in text for token in ("llm", "language model", "large language", "gpt", "instruction")):
        return "大语言模型与知识组织"
    if any(token in text for token in ("diffusion", "generative", "gan", "mattergen", "design")):
        return "生成模型驱动的设计与发现"
    if any(token in text for token in ("multimodal", "vision", "graph", "retrieval", "rag")):
        return "多模态建模与知识增强"
    if any(token in text for token in ("benchmark", "evaluation", "survey", "review", "assessment")):
        return "评测基准与方法比较"
    return "交叉方法与应用场景"


def _format_wikilink(paper: dict[str, Any]) -> str:
    note_path = str(paper.get("relative_note_path", "")).strip()
    citekey = str(paper.get("citekey", "")).strip()
    title = str(paper.get("title", "")).strip() or "未命名文献"
    year = str(paper.get("year", "")).strip()
    label = citekey or title
    if note_path:
        rendered = f"[[{note_path}|{label}]]"
    else:
        rendered = label
    if year:
        return f"{rendered}（{year}）"
    return rendered


def _format_reference_line(paper: dict[str, Any]) -> str:
    parts = [_format_wikilink(paper)]
    title = str(paper.get("title", "")).strip()
    if title and title not in parts[0]:
        parts.append(title)
    summary = str(paper.get("one_sentence_summary", "")).strip()
    if summary:
        parts.append(summary)
    return "：".join([parts[0], "；".join(parts[1:])]) if len(parts) > 1 else parts[0]


def _collect_top_keywords(papers: list[dict[str, Any]], topic: str) -> list[str]:
    counter: Counter[str] = Counter()
    for paper in papers:
        corpus = "\n".join(
            [
                str(paper.get("title", "")),
                str(paper.get("one_sentence_summary", "")),
                str(paper.get("methods_summary", "")),
            ]
        ).lower()
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", corpus):
            if token in {
                "and", "for", "the", "with", "from", "using", "that", "this",
                "review", "survey", "materials", "material", "model", "models",
            }:
                continue
            counter[token] += 1

    keywords = [topic.strip()] if topic.strip() else []
    for token, _count in counter.most_common(5):
        if token not in keywords:
            keywords.append(token)
    if "文献综述" not in keywords:
        keywords.append("文献综述")
    return keywords[:6]


def _paper_payload(summary: dict[str, Any], evidence: dict[str, Any], imported_note_path: str) -> dict[str, Any]:
    intro_row = next(
        (
            row for row in (evidence.get("evidence_pages") or [])
            if isinstance(row, dict) and row.get("section") == "introduction"
        ),
        {},
    )
    methods_row = next(
        (
            row for row in (evidence.get("evidence_pages") or [])
            if isinstance(row, dict) and row.get("section") == "methods"
        ),
        {},
    )
    findings_row = next(
        (
            row for row in (evidence.get("evidence_pages") or [])
            if isinstance(row, dict) and row.get("section") == "findings"
        ),
        {},
    )
    return {
        "title": str(evidence.get("title", "") or summary.get("title", "")).strip(),
        "citekey": str(evidence.get("citekey", "") or summary.get("citekey", "")).strip(),
        "year": str(evidence.get("year", "") or summary.get("year", "")).strip(),
        "doi": str(evidence.get("doi", "") or summary.get("doi", "")).strip(),
        "relative_note_path": imported_note_path,
        "one_sentence_summary": str(evidence.get("one_sentence_summary", "") or summary.get("one_sentence_summary", "")).strip(),
        "abstract": _clean_text(evidence.get("abstract_from_json", "")),
        "fulltext_excerpt": _clean_text(evidence.get("fulltext_excerpt", "")),
        "methods_summary": _clean_text(evidence.get("methods_summary", "")),
        "key_findings": _clean_text(evidence.get("key_findings", "")),
        "limitations": _clean_text(evidence.get("limitations", "")),
        "section_hint": str(evidence.get("section_hint", "") or summary.get("section_hint", "")).strip(),
        "theme_label": _guess_theme_label(evidence),
        "preferred_summary_source": str(evidence.get("preferred_summary_source", "")).strip(),
        "attachment_pdf_path": str(evidence.get("attachment_pdf_path", "")).strip(),
        "metadata_conflict": bool(evidence.get("metadata_conflict", False)),
        "metadata_conflict_reason": str(evidence.get("metadata_conflict_reason", "")).strip(),
        "relevance_label": str(evidence.get("relevance_label", "") or summary.get("relevance_label", "")).strip(),
        "relevance_reason": str(evidence.get("relevance_reason", "") or summary.get("relevance_reason", "")).strip(),
        "page_excerpts": [
            _make_page_excerpt("introduction", intro_row, evidence.get("fulltext_excerpt", "")),
            _make_page_excerpt("methods", methods_row, evidence.get("methods_summary", "")),
            _make_page_excerpt("findings", findings_row, evidence.get("key_findings", "")),
        ],
        "source_diagnostics": evidence.get("source_diagnostics", {}),
    }


def _load_paper_payloads(
    bundle: dict[str, Any],
    evidence_dir: Path,
    imported_note_paths: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    evidence_map: dict[str, dict[str, Any]] = {}
    for evidence_file in sorted(evidence_dir.glob("*.json")):
        try:
            evidence = _load_json(evidence_file)
        except Exception as exc:
            logger.warning("[obsidian_run_zotero_review_agent] failed to read evidence %s: %s", evidence_file, exc)
            continue
        citekey = str(evidence.get("citekey", "")).strip()
        if citekey:
            evidence_map[citekey] = evidence

    payloads: dict[str, list[dict[str, Any]]] = {"core": [], "boundary": [], "noise": []}
    for label in ("core", "boundary", "noise"):
        for row in bundle.get(f"{label}_papers", []) or []:
            if not isinstance(row, dict):
                continue
            citekey = str(row.get("citekey", "")).strip()
            evidence = evidence_map.get(citekey, {})
            payloads[label].append(
                _paper_payload(
                    summary=row,
                    evidence=evidence,
                    imported_note_path=imported_note_paths.get(citekey, ""),
                )
            )
    return payloads


def _build_pdf_stats(payloads: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    all_papers = payloads["core"] + payloads["boundary"] + payloads["noise"]
    method_counter: Counter[str] = Counter()
    missing_pdf_titles: list[str] = []
    accessible_pdf_count = 0
    fulltext_ready_count = 0
    metadata_conflict_count = 0

    for paper in all_papers:
        diagnostics = paper.get("source_diagnostics", {}) or {}
        extraction_method = str(diagnostics.get("extraction_method", "")).strip()
        if extraction_method:
            method_counter[extraction_method] += 1
            fulltext_ready_count += 1
        if str(paper.get("attachment_pdf_path", "")).strip():
            accessible_pdf_count += 1
        if diagnostics.get("pdf_unavailable"):
            missing_pdf_titles.append(str(paper.get("title", "")).strip() or "Untitled")
        if paper.get("metadata_conflict"):
            metadata_conflict_count += 1

    return {
        "total_papers": len(all_papers),
        "accessible_pdf_count": accessible_pdf_count,
        "fulltext_ready_count": fulltext_ready_count,
        "missing_pdf_count": len(missing_pdf_titles),
        "missing_pdf_titles": missing_pdf_titles,
        "extraction_method_counts": dict(method_counter),
        "metadata_conflict_count": metadata_conflict_count,
    }


def _build_warnings(
    import_result: dict[str, Any],
    pdf_stats: dict[str, Any],
    payloads: dict[str, list[dict[str, Any]]],
) -> list[str]:
    warnings: list[str] = []
    skipped_count = int(import_result.get("skipped_count", 0) or 0)
    if skipped_count:
        warnings.append(f"有 {skipped_count} 篇条目在导入文献笔记时被跳过，请检查是否已存在同名笔记或写入失败。")

    missing_pdf_count = int(pdf_stats.get("missing_pdf_count", 0) or 0)
    if missing_pdf_count:
        warnings.append(f"有 {missing_pdf_count} 篇文献未找到可访问 PDF，相关综述内容将更多依赖导出摘要。")

    conflict_count = int(pdf_stats.get("metadata_conflict_count", 0) or 0)
    if conflict_count:
        warnings.append(f"检测到 {conflict_count} 篇文献存在题目与摘要语义不一致，已优先使用全文片段。")

    if not payloads["core"] and payloads["boundary"]:
        warnings.append("当前主题下没有明显核心文献，本次综述主要依据边界相关文献组织。")
    if not (payloads["core"] or payloads["boundary"]):
        warnings.append("没有筛选出可纳入综述的文献，请检查导出主题是否正确。")
    return warnings


def _render_theme_section(theme: str, papers: list[dict[str, Any]]) -> str:
    if not papers:
        return ""

    lead = papers[0]
    lead_summary = lead.get("one_sentence_summary") or lead.get("key_findings") or "该方向仍需补充更多摘要。"
    citations = "、".join(_format_wikilink(paper) for paper in papers[:4])
    details: list[str] = []
    for paper in papers[:3]:
        finding = _normalize_whitespace(
            paper.get("key_findings") or paper.get("methods_summary") or paper.get("fulltext_excerpt")
        )
        if not finding:
            continue
        finding = finding[:220].rstrip()
        details.append(f"{_format_wikilink(paper)}指出{finding}")

    paragraph = (
        f"### {theme}\n\n"
        f"围绕“{theme}”这一方向，当前证据主要由{citations}等工作构成。"
        f"综合这些文献可以看到，{lead_summary}"
    )
    if details:
        paragraph += "进一步来看，" + "；".join(details) + "。"

    limitations = [
        _normalize_whitespace(paper.get("limitations", ""))[:160].rstrip()
        for paper in papers[:3]
        if _normalize_whitespace(paper.get("limitations", ""))
    ]
    if limitations:
        paragraph += "不过，这一方向仍面临" + "；".join(limitations) + "等约束。"
    return paragraph.strip()


def _render_challenge_paragraph(papers: list[dict[str, Any]]) -> str:
    limitation_bits: list[str] = []
    for paper in papers[:5]:
        limitation = _normalize_whitespace(paper.get("limitations", ""))
        if not limitation:
            continue
        limitation_bits.append(f"{_format_wikilink(paper)}提到{limitation[:180].rstrip()}")
    if not limitation_bits:
        return (
            "现有研究普遍仍受限于数据覆盖范围、任务定义一致性、全文证据可得性以及跨场景泛化能力，"
            "这意味着后续综述和实验设计仍需要结合原文逐篇复核。"
        )
    return "综合纳入文献的局限性描述可以看到，" + "；".join(limitation_bits) + "。"


def _render_future_paragraph(topic: str, payloads: dict[str, list[dict[str, Any]]], pdf_stats: dict[str, Any]) -> str:
    boundary_papers = payloads.get("boundary") or payloads.get("boundary_papers") or []
    core_papers = payloads.get("core") or payloads.get("core_papers") or []
    opportunities: list[str] = []
    if int(pdf_stats.get("missing_pdf_count", 0) or 0):
        opportunities.append("补全缺失全文并重新核对证据页码")
    if boundary_papers:
        opportunities.append("围绕边界文献建立更清晰的纳入/排除标准")
    if core_papers:
        opportunities.append("把核心文献中的方法链路和评价指标整理成统一比较框架")
    opportunities.append("将综述结论继续沉淀为 Obsidian 项目笔记与写作提纲")
    return f"针对“{topic}”主题，下一步更有价值的工作包括" + "、".join(opportunities) + "。"


def _render_review_draft(topic: str, export_path: Path, writing_input: dict[str, Any], pdf_stats: dict[str, Any]) -> str:
    core_papers = writing_input.get("core_papers", [])
    boundary_papers = writing_input.get("boundary_papers", [])
    included_papers = writing_input.get("included_papers", [])
    noise_papers = writing_input.get("noise_papers", [])
    theme_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in included_papers:
        theme_map[str(paper.get("theme_label", "")).strip() or "交叉方法与应用场景"].append(paper)

    keywords = writing_input.get("keywords", [])
    keyword_line = "；".join(str(keyword).strip() for keyword in keywords if str(keyword).strip())
    first_core = core_papers[0] if core_papers else (boundary_papers[0] if boundary_papers else {})

    abstract_lines = [
        f"本文基于本地 Zotero Better BibTeX 导出 `{export_path}` 及其可访问附件 PDF，对“{topic}”相关文献进行了自动化梳理。",
        f"本轮共处理 {writing_input.get('processed_parent_items', 0)} 篇父条目，其中核心文献 {len(core_papers)} 篇、边界文献 {len(boundary_papers)} 篇、排除文献 {len(noise_papers)} 篇。",
        f"在全文证据层面，共有 {pdf_stats.get('fulltext_ready_count', 0)} 篇文献成功提取到可读全文，"
        f"其余条目则回退为导出摘要或元数据。",
    ]
    if first_core:
        abstract_lines.append(
            f"从当前证据看，{_format_wikilink(first_core)}代表的研究最能体现该主题的主线进展，"
            f"其核心结论是{first_core.get('one_sentence_summary', '当前仍需进一步归纳').strip()}。"
        )

    intro = (
        f"本综述以本地知识管理链路为前提，结合 Zotero 导出的题录、摘要、附件路径以及 Obsidian 文献卡片，"
        f"对“{topic}”主题进行可追溯的中文综述整理。与只依赖摘要的快速综述不同，本次流程优先读取可访问 PDF 全文，"
        f"并将证据页码、方法摘要和关键发现回写到统一 review note 中，便于后续继续扩展到写作和项目笔记。"
    )

    evidence_base = (
        f"证据基础方面，本轮共纳入 {len(included_papers)} 篇文献进入主综述视角，其中"
        f"核心文献 {len(core_papers)} 篇、边界文献 {len(boundary_papers)} 篇。"
        f"另外有 {len(noise_papers)} 篇条目被判定为噪声或与主题弱相关，因此仅保留在 bundle 中作为排除记录。"
        f"全文可读率与元数据一致性检查表明，当前链路已经能够支撑以证据为中心的综述写作，但仍需对缺失 PDF 的条目进行补充。"
    )

    comparison_lines: list[str] = []
    for paper in (core_papers[:3] + boundary_papers[:2]):
        finding = _normalize_whitespace(paper.get("key_findings", "") or paper.get("methods_summary", ""))
        if not finding:
            continue
        comparison_lines.append(f"{_format_wikilink(paper)}强调{finding[:220].rstrip()}")
    comparison = (
        "从代表性工作比较来看，" + "；".join(comparison_lines) + "。"
        if comparison_lines
        else "当前代表性工作之间的差异主要体现在研究对象、评价指标以及是否具备完整全文证据三个层面。"
    )

    references = "\n".join(f"- {_format_reference_line(paper)}" for paper in included_papers) or "- 暂无可引用文献。"

    theme_sections = "\n\n".join(
        section for section in (
            _render_theme_section(theme, papers)
            for theme, papers in sorted(theme_map.items(), key=lambda item: (-len(item[1]), item[0]))
        )
        if section
    ) or "### 主要方向待补充\n\n当前尚未形成足够稳定的主题分组，建议先补全全文后再细化方向章节。"

    challenge_text = _render_challenge_paragraph(included_papers)
    future_text = _render_future_paragraph(topic, writing_input, pdf_stats)
    conclusion_text = (
        f"总体而言，当前 Zotero Review Agent 已经能够围绕“{topic}”形成从题录导入、全文证据抽取、中文综述草稿生成到 Obsidian 落盘的闭环。"
        f"后续只需在此基础上继续人工校对关键论断与引用细节，就可以进一步扩展为论文写作、项目策划或长期知识库维护。"
    )

    return "\n".join(
        [
            f"# {topic}",
            "",
            "> [!info] 生成说明",
            f"> 本综述由 ScienceClaw 基于本地 Zotero Better BibTeX 导出与附件全文自动生成，并写回同一份 Obsidian review note。",
            "",
            "## 摘要",
            "".join(abstract_lines),
            "",
            "## 关键词",
            keyword_line or "待补充",
            "",
            "## 引言",
            intro,
            "",
            "## 证据基础与研究版图",
            evidence_base,
            "",
            "## 主要研究方向",
            theme_sections,
            "",
            "## 代表性工作比较与讨论",
            comparison,
            "",
            "## 挑战与争议",
            challenge_text,
            "",
            "## 未来趋势与机会",
            future_text,
            "",
            "## 结论",
            conclusion_text,
            "",
            "## 参考文献",
            references,
            "",
        ]
    ).strip() + "\n"


def _write_review_artifacts(
    export_path: Path,
    topic: str,
    writing_input: dict[str, Any],
    draft_markdown: str,
    artifacts_dir: str = "",
) -> tuple[str, str]:
    slug = _safe_slug(topic, "review-agent")
    research_data_dir = Path(str(artifacts_dir or "").strip()) if str(artifacts_dir or "").strip() else (
        export_path.parent.parent / "research_data" if export_path.parent.name.lower() == "zotero" else export_path.parent / "research_data"
    )
    research_data_dir.mkdir(parents=True, exist_ok=True)

    review_input_path = research_data_dir / f"{slug}-review-agent-input.json"
    review_input_path.write_text(json.dumps(writing_input, ensure_ascii=False, indent=2), encoding="utf-8")

    review_draft_path = research_data_dir / f"{slug}-review-agent-draft.md"
    review_draft_path.write_text(draft_markdown, encoding="utf-8")
    return str(review_input_path), str(review_draft_path)


@tool
def obsidian_run_zotero_review_agent(
    export_json_path: str,
    topic: str = "",
    category: str = "",
    vault_dir: str = "",
    overwrite_existing: bool = False,
    max_items: int = 0,
) -> dict:
    """Run the local Zotero -> review-bundle -> Chinese review -> Obsidian workflow.

    Use this tool when the user wants an end-to-end Zotero Review Agent run:
    validate a Better BibTeX export, build full-text evidence, generate/update
    literature and review notes in Obsidian, and prepare a structured review
    writing package for follow-up refinement.
    """
    logger.info(
        "[obsidian_run_zotero_review_agent] export_json_path=%r topic=%r vault_dir=%r overwrite_existing=%s max_items=%s",
        export_json_path,
        topic,
        vault_dir,
        overwrite_existing,
        max_items,
    )

    export_path = _resolve_path(export_json_path)
    if not export_path.exists():
        return {"ok": False, "error": f"Export JSON not found: {export_path}"}

    try:
        payload = _load_json(export_path)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON: {exc}"}

    valid, validation_error, parent_items = _validate_bbt_export(payload)
    if not valid:
        return {"ok": False, "error": validation_error}

    resolved_topic = topic.strip() or export_path.stem
    resolved_category = _normalize_category(category, resolved_topic)
    build_bundle = _load_bundle_tool()
    import_tool = _load_import_tool()
    writer_tool = _load_writer_tool()

    bundle_result = build_bundle.invoke(
        {
            "export_json_path": str(export_path),
            "topic": resolved_topic,
            "category": resolved_category,
            "language": "zh",
            "prefer_pdf_fulltext": True,
            "relevance_policy": "balanced",
            "max_items": max_items,
        }
    )
    if not bundle_result.get("ok"):
        return {
            "ok": False,
            "error": bundle_result.get("error", "Failed to build Zotero review bundle"),
            "topic": resolved_topic,
        }

    import_result = import_tool.invoke(
        {
            "export_json_path": str(export_path),
            "topic": resolved_topic,
            "category": resolved_category,
            "max_items": max_items,
            "vault_dir": vault_dir,
            "overwrite_existing": overwrite_existing,
            "create_review_note": True,
        }
    )
    if not import_result.get("ok"):
        return {
            "ok": False,
            "error": import_result.get("error", "Failed to import Zotero export into Obsidian"),
            "topic": resolved_topic,
            "bundle_path": bundle_result.get("review_bundle_path", ""),
            "bootstrap_result": import_result.get("bootstrap_result"),
            "requested_vault_dir": import_result.get("requested_vault_dir", ""),
            "effective_vault_dir": import_result.get("effective_vault_dir", ""),
            "effective_vault_source": import_result.get("effective_vault_source", ""),
            "fell_back_to_default_vault": import_result.get("fell_back_to_default_vault", False),
            "vault_match_status": import_result.get("vault_match_status", "exact"),
            "required_skills": import_result.get("required_skills", _REQUIRED_LOCAL_SKILLS),
            "read_skills": import_result.get("read_skills", []),
            "missing_required_skills": import_result.get("missing_required_skills", []),
        }

    if not overwrite_existing and not str(import_result.get("review_note_path", "")).strip():
        return {
            "ok": False,
            "error": (
                f"Review note already exists for topic '{resolved_topic}'. "
                "Set overwrite_existing=true to replace it."
            ),
            "topic": resolved_topic,
            "bundle_path": str(bundle_result.get("review_bundle_path", "")),
            "requested_vault_dir": import_result.get("requested_vault_dir", str(vault_dir or "").strip()),
            "effective_vault_dir": import_result.get("effective_vault_dir", import_result.get("vault_dir", "")),
            "effective_vault_source": import_result.get("effective_vault_source", import_result.get("vault_source", "")),
            "fell_back_to_default_vault": import_result.get("fell_back_to_default_vault", False),
            "vault_match_status": import_result.get("vault_match_status", "exact"),
            "required_skills": import_result.get("required_skills", _REQUIRED_LOCAL_SKILLS),
            "read_skills": import_result.get("read_skills", []),
            "missing_required_skills": import_result.get("missing_required_skills", []),
        }

    bundle_path = Path(str(bundle_result.get("review_bundle_path", "")))
    evidence_dir = Path(str(bundle_result.get("paper_evidence_dir", "")))
    if not bundle_path.exists():
        return {
            "ok": False,
            "error": f"Review bundle file missing after build step: {bundle_path}",
            "topic": resolved_topic,
        }
    bundle = _load_json(bundle_path)

    imported_note_paths = {
        str(row.get("citekey", "")).strip(): str(row.get("relative_note_path", "")).strip()
        for row in (import_result.get("imported_notes") or [])
        if isinstance(row, dict) and str(row.get("citekey", "")).strip()
    }
    payloads = _load_paper_payloads(bundle, evidence_dir, imported_note_paths)
    included_papers = payloads["core"] + payloads["boundary"]
    pdf_stats = _build_pdf_stats(payloads)

    writing_input = {
        "topic": resolved_topic,
        "category": resolved_category,
        "language": "zh",
        "source_export_json": str(export_path),
        "review_note_path": str(import_result.get("review_note_path", "")).strip(),
        "bundle_path": str(bundle_path),
        "paper_evidence_dir": str(evidence_dir),
        "processed_parent_items": int(bundle_result.get("processed_parent_items", len(parent_items)) or 0),
        "core_papers": payloads["core"],
        "boundary_papers": payloads["boundary"],
        "noise_papers": payloads["noise"],
        "included_papers": included_papers,
        "keywords": _collect_top_keywords(included_papers, resolved_topic),
        "metadata_conflicts": bundle.get("metadata_conflicts", []),
        "section_hints": bundle.get("section_hints", []),
        "pdf_stats": pdf_stats,
        "imported_notes": import_result.get("imported_notes", []),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "skill_pipeline": list(_REQUIRED_LOCAL_SKILLS),
        "required_skills": list(_REQUIRED_LOCAL_SKILLS),
        "read_skills": [],
        "missing_required_skills": list(_REQUIRED_LOCAL_SKILLS),
    }

    warnings = _build_warnings(import_result, pdf_stats, payloads)
    writing_input["warnings"] = warnings

    template_markdown = _render_review_draft(
        topic=resolved_topic,
        export_path=export_path,
        writing_input=writing_input,
        pdf_stats=pdf_stats,
    )
    polish_result = _polish_review_with_local_skills(
        topic=resolved_topic,
        draft_markdown=template_markdown,
        writing_input=writing_input,
        review_note_path=str(import_result.get("review_note_path", "")).strip(),
    )
    if not polish_result.get("ok"):
        return {
            "ok": False,
            "error": polish_result.get("error", "Failed to run skill-driven final rewrite"),
            "topic": resolved_topic,
            "bundle_path": str(bundle_path),
            "requested_vault_dir": import_result.get("requested_vault_dir", str(vault_dir or "").strip()),
            "effective_vault_dir": import_result.get("effective_vault_dir", import_result.get("vault_dir", "")),
            "effective_vault_source": import_result.get("effective_vault_source", import_result.get("vault_source", "")),
            "fell_back_to_default_vault": import_result.get("fell_back_to_default_vault", False),
            "vault_match_status": import_result.get("vault_match_status", "exact"),
            "required_skills": list(_REQUIRED_LOCAL_SKILLS),
            "read_skills": polish_result.get("read_skills", []),
            "missing_required_skills": polish_result.get("missing_required_skills", list(_REQUIRED_LOCAL_SKILLS)),
        }
    writing_input["read_skills"] = polish_result.get("read_skills", [])
    writing_input["missing_required_skills"] = polish_result.get("missing_required_skills", [])
    draft_markdown = str(polish_result.get("markdown", "")).strip()
    review_input_path, review_draft_path = _write_review_artifacts(
        export_path=export_path,
        topic=resolved_topic,
        writing_input=writing_input,
        draft_markdown=draft_markdown,
        artifacts_dir=str(bundle_path.parent),
    )

    review_metadata = {
        "title": resolved_topic,
        "topic": resolved_topic,
        "category": resolved_category,
        "keywords": writing_input["keywords"],
        "tags": ["materials-review", "zotero-review-agent", "zotero-import"],
        "review_bundle_path": str(bundle_path),
        "source_export_json": str(export_path),
        "writing_pass": "scientific-writing",
        "skill_pipeline": writing_input["skill_pipeline"],
        "required_skills": writing_input["required_skills"],
        "read_skills": writing_input["read_skills"],
        "missing_required_skills": writing_input["missing_required_skills"],
        "review_input_path": review_input_path,
        "review_draft_path": review_draft_path,
        "source_writing_input_path": review_input_path,
        "included_paper_count": len(included_papers),
        "boundary_paper_count": len(payloads["boundary"]),
        "noise_paper_count": len(payloads["noise"]),
        "pdf_stats": pdf_stats,
        "references": [
            {
                "title": paper.get("title", ""),
                "citekey": paper.get("citekey", ""),
                "year": paper.get("year", ""),
                "relative_note_path": paper.get("relative_note_path", ""),
                "one_sentence_summary": paper.get("one_sentence_summary", ""),
            }
            for paper in included_papers
        ],
    }
    final_review_result = writer_tool.invoke(
        {
            "note_type": "review",
            "title": resolved_topic,
            "content": draft_markdown,
            "metadata_json": json.dumps(review_metadata, ensure_ascii=False),
            "project_name": resolved_topic,
            "category": resolved_category,
            "vault_dir": vault_dir,
            "overwrite": True,
            "review_style": "survey_cn",
            "filename_style": "title-review",
            "conflict_mode": "error",
        }
    )
    if not final_review_result.get("ok"):
        return {
            "ok": False,
            "error": final_review_result.get("error", "Failed to write final review note"),
            "topic": resolved_topic,
            "bundle_path": str(bundle_path),
            "review_input_path": review_input_path,
            "review_draft_path": review_draft_path,
            "requested_vault_dir": final_review_result.get("requested_vault_dir", import_result.get("requested_vault_dir", str(vault_dir or "").strip())),
            "effective_vault_dir": final_review_result.get("effective_vault_dir", import_result.get("effective_vault_dir", "")),
            "effective_vault_source": final_review_result.get("effective_vault_source", import_result.get("effective_vault_source", "")),
            "fell_back_to_default_vault": final_review_result.get("fell_back_to_default_vault", import_result.get("fell_back_to_default_vault", False)),
            "vault_match_status": final_review_result.get("vault_match_status", import_result.get("vault_match_status", "exact")),
            "required_skills": final_review_result.get("required_skills", writing_input["required_skills"]),
            "read_skills": final_review_result.get("read_skills", writing_input["read_skills"]),
            "missing_required_skills": final_review_result.get("missing_required_skills", writing_input["missing_required_skills"]),
        }

    literature_note_paths = [
        str(row.get("relative_note_path", "")).strip()
        for row in (import_result.get("imported_notes") or [])
        if isinstance(row, dict) and str(row.get("relative_note_path", "")).strip()
    ]

    return {
        "ok": True,
        "topic": resolved_topic,
        "category": resolved_category,
        "vault_dir": final_review_result.get("effective_vault_dir", import_result.get("effective_vault_dir", import_result.get("vault_dir", ""))),
        "requested_vault_dir": final_review_result.get("requested_vault_dir", import_result.get("requested_vault_dir", str(vault_dir or "").strip())),
        "effective_vault_dir": final_review_result.get("effective_vault_dir", import_result.get("effective_vault_dir", import_result.get("vault_dir", ""))),
        "effective_vault_source": final_review_result.get("effective_vault_source", import_result.get("effective_vault_source", import_result.get("vault_source", ""))),
        "fell_back_to_default_vault": final_review_result.get("fell_back_to_default_vault", import_result.get("fell_back_to_default_vault", False)),
        "vault_match_status": final_review_result.get("vault_match_status", import_result.get("vault_match_status", "exact")),
        "bundle_path": str(bundle_path),
        "review_note_path": str(final_review_result.get("note_path", final_review_result.get("relative_note_path", ""))).strip(),
        "review_input_path": review_input_path,
        "review_draft_path": review_draft_path,
        "literature_note_paths": literature_note_paths,
        "import_stats": {
            "processed_parent_items": int(import_result.get("processed_parent_items", 0) or 0),
            "imported_count": int(import_result.get("imported_count", 0) or 0),
            "skipped_count": int(import_result.get("skipped_count", 0) or 0),
        },
        "pdf_stats": pdf_stats,
        "warnings": warnings,
        "skill_pipeline": writing_input["skill_pipeline"],
        "required_skills": final_review_result.get("required_skills", writing_input["required_skills"]),
        "read_skills": final_review_result.get("read_skills", writing_input["read_skills"]),
        "missing_required_skills": final_review_result.get("missing_required_skills", writing_input["missing_required_skills"]),
        "generated_at": writing_input["generated_at"],
    }
