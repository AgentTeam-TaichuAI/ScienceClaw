import base64
import importlib.util
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx
import yaml
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Obsidian",
    "subcategory": "Review Agent",
    "tags": ["obsidian", "review", "rewrite", "zotero", "scientific-writing"],
}

_TOOL_CACHE: dict[str, Any] = {}
_REQUIRED_LOCAL_SKILLS = [
    "zotero-materials-review",
    "literature-review",
    "scientific-writing",
    "obsidian-markdown",
    "materials-obsidian",
]
_GBT_RE = re.compile(r"gb/?t\s*7714|gb7714", re.IGNORECASE)
_ACADEMIC_STYLE_RE = re.compile(
    r"(科研|论文|学术|journal|academic|scientific|润色|改写|改成|重写|规范)",
    re.IGNORECASE,
)
_INFO_CALLOUT_RE = re.compile(r"(?ms)^> \[!info\].*?(?:\n\n|$)")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_HOST_BRIDGE_CANDIDATES = [
    "http://127.0.0.1:8765",
    "http://host.docker.internal:8765",
]


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
    if tool_obj is None:
        raise RuntimeError(f"Missing attribute {attr_name} in {tool_path}")

    _TOOL_CACHE[cache_key] = tool_obj
    return tool_obj


def _load_writer_tool():
    writer = _load_tool("obsidian_write_materials_note.py", "obsidian_write_materials_note")
    if not hasattr(writer, "invoke"):
        raise RuntimeError("obsidian_write_materials_note tool is unavailable")
    return writer


def _load_review_renderer():
    renderer = _load_tool("obsidian_run_zotero_review_agent.py", "_render_review_draft")
    if not callable(renderer):
        raise RuntimeError("_render_review_draft is unavailable")
    return renderer


def _load_skill_rewriter():
    rewriter = _load_tool("obsidian_run_zotero_review_agent.py", "_polish_review_with_local_skills")
    if not callable(rewriter):
        raise RuntimeError("_polish_review_with_local_skills is unavailable")
    return rewriter


def _is_windows_host_path(raw_path: str) -> bool:
    return bool(_WINDOWS_DRIVE_RE.match(str(raw_path or "").strip()))


def _bridge_headers() -> dict[str, str]:
    return {
        "X-Bridge-Token": os.environ.get("OBSIDIAN_HOST_BRIDGE_TOKEN", "scienceclaw-local-bridge"),
    }


def _bridge_candidates() -> list[str]:
    configured = (os.environ.get("OBSIDIAN_HOST_BRIDGE_URL", "") or "").strip()
    candidates: list[str] = []
    if configured:
        candidates.append(configured.rstrip("/"))
    for candidate in _HOST_BRIDGE_CANDIDATES:
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _host_read_file(path: str, timeout: float = 30.0) -> dict[str, Any]:
    last_error: Exception | None = None
    payload = {"path": path}
    for base_url in _bridge_candidates():
        try:
            response = httpx.post(
                f"{base_url}/host/read-file",
                json=payload,
                headers=_bridge_headers(),
                timeout=timeout,
                trust_env=False,
            )
            data = response.json() if response.content else {}
            return {
                "ok": response.is_success,
                "status_code": response.status_code,
                "bridge_url": base_url,
                "data": data,
            }
        except Exception as exc:  # pragma: no cover - network guardrail
            last_error = exc
    return {
        "ok": False,
        "status_code": 503,
        "bridge_url": "",
        "data": {
            "ok": False,
            "error": f"Host bridge unavailable: {last_error}" if last_error else "Host bridge unavailable",
        },
    }


def _resolve_path(raw_path: str, base_dir: Path | None = None) -> Path:
    path = Path(str(raw_path or "").strip()).expanduser()
    if not path.is_absolute():
        path = (base_dir or Path.cwd()) / path
    return path


def _fallback_local_candidates(raw_path: str) -> list[Path]:
    raw = str(raw_path or "").strip()
    if not raw:
        return []
    basename = Path(raw).name
    candidates = [
        Path.cwd() / "research_data" / basename,
        Path.cwd() / basename,
    ]
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = text.replace("\x00", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_note_text(value: Any) -> str:
    text = str(value or "")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _safe_slug(value: str, fallback: str = "review") -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", str(value or ""), flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-_")
    return slug or fallback


def _safe_folder_component(value: str, fallback: str = "") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n]+', " ", str(value or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned[:120].strip()
    return cleaned or fallback


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    normalized = _normalize_note_text(text)
    if not normalized.startswith("---\n"):
        return {}, normalized

    match = re.match(r"(?s)\A---\n(.*?)\n---\n?(.*)\Z", normalized)
    if not match:
        return {}, normalized

    raw_frontmatter = match.group(1)
    body = match.group(2)
    try:
        frontmatter = yaml.safe_load(raw_frontmatter) or {}
    except Exception:
        frontmatter = {}
    return frontmatter if isinstance(frontmatter, dict) else {}, body


def _extract_embedded_frontmatter_from_body(body: str) -> tuple[dict[str, Any], str]:
    normalized = _normalize_note_text(body).lstrip("\n")
    match = re.match(r"(?s)\A(?P<prefix>(?:# .+\n(?:\n)*)?)---\n(?P<yaml>.*?)\n---\n?(?P<rest>.*)\Z", normalized)
    if not match:
        return {}, normalized

    try:
        embedded_frontmatter = yaml.safe_load(match.group("yaml")) or {}
    except Exception:
        return {}, normalized
    if not isinstance(embedded_frontmatter, dict):
        return {}, normalized

    prefix = match.group("prefix").rstrip()
    rest = match.group("rest").lstrip("\n")
    cleaned_parts = [part for part in [prefix, rest] if part]
    cleaned_body = "\n\n".join(cleaned_parts).strip()
    return embedded_frontmatter, cleaned_body


def _merge_frontmatter(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary or {})
    for key, value in (fallback or {}).items():
        existing = merged.get(key)
        if existing in (None, "", [], {}):
            merged[key] = value
    return merged


def _coalesce_first_nonempty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return ""


def _has_usable_writing_input(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    return any(
        payload.get(key) not in (None, "", [], {})
        for key in (
            "included_papers",
            "core_papers",
            "boundary_papers",
            "bundle_path",
            "source_export_json",
            "pdf_stats",
        )
    )


def _source_writing_input_candidates(
    topic: str,
    review_input_path: str,
    source_writing_input_path: str,
    loaded_review_input: Any,
    frontmatter: dict[str, Any],
    payload_frontmatter: dict[str, Any],
) -> list[str]:
    slug = _safe_slug(topic, "review")
    candidates = [
        source_writing_input_path,
        review_input_path,
        str(frontmatter.get("source_writing_input_path", "")).strip(),
        str(payload_frontmatter.get("source_writing_input_path", "")).strip(),
        str(frontmatter.get("review_input_path", "")).strip(),
        str(payload_frontmatter.get("review_input_path", "")).strip(),
        str((loaded_review_input or {}).get("source_writing_input_path", "")).strip() if isinstance(loaded_review_input, dict) else "",
        str((loaded_review_input or {}).get("review_input_path", "")).strip() if isinstance(loaded_review_input, dict) else "",
        str(Path.cwd() / "research_data" / f"{slug}-review-agent-input.json"),
        str(Path(__file__).resolve().parent.parent / "research_data" / f"{slug}-review-agent-input.json"),
        f"/home/scienceclaw/uploads/research_data/{slug}-review-agent-input.json",
    ]

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _infer_vault_dir_from_note_path(note_path: str) -> str:
    raw = str(note_path or "").strip()
    if not raw:
        return ""
    if _is_windows_host_path(raw):
        normalized = raw.replace("/", "\\")
        parts = [part for part in normalized.split("\\") if part]
        lowered = [part.lower() for part in parts]
        marker = ["research", "materials", "review notes"]
        for index in range(len(lowered) - 2):
            if lowered[index:index + 3] == marker:
                prefix = parts[:index]
                if not prefix:
                    return ""
                drive = prefix[0]
                tail = "\\".join(prefix[1:])
                return drive if not tail else f"{drive}\\{tail}"
        return ""

    path = _resolve_path(raw)
    parts = list(path.parts)
    lowered = [part.lower() for part in parts]
    marker = ["research", "materials", "review notes"]
    for index in range(len(lowered) - 2):
        if lowered[index:index + 3] == marker:
            return str(Path(*parts[:index]))
    return ""


def _infer_review_note_path(review_note_path: str, topic: str, vault_dir: str, category: str = "") -> str:
    raw_review_note_path = str(review_note_path or "").strip()
    raw_vault_dir = str(vault_dir or "").strip()
    if raw_review_note_path:
        if _is_windows_host_path(raw_review_note_path):
            return raw_review_note_path.replace("/", "\\")
        if Path(raw_review_note_path).is_absolute():
            return str(_resolve_path(raw_review_note_path))
        if not raw_vault_dir:
            raise ValueError("vault_dir is required when review_note_path is relative")
        if _is_windows_host_path(raw_vault_dir):
            return f"{raw_vault_dir.rstrip('/\\')}\\{raw_review_note_path.replace('/', '\\')}"
        return str(_resolve_path(raw_review_note_path, base_dir=_resolve_path(raw_vault_dir)))

    if not str(topic or "").strip():
        raise ValueError("Either review_note_path or topic is required")
    if not raw_vault_dir:
        raise ValueError("vault_dir is required when resolving review note by topic")

    relative_dir = "Research/Materials/Review Notes"
    category_dir = _safe_folder_component(category)
    if category_dir:
        relative_dir = f"{relative_dir}/{category_dir}"
    relative_path = f"{relative_dir}/{_safe_folder_component(topic, 'materials-topic')} - review.md"
    if _is_windows_host_path(raw_vault_dir):
        return f"{raw_vault_dir.rstrip('/\\')}\\{relative_path.replace('/', '\\')}"
    return str(_resolve_path(relative_path, base_dir=_resolve_path(raw_vault_dir)))


def _read_text_result(raw_path: str) -> dict[str, Any]:
    target = str(raw_path or "").strip()
    if not target:
        return {"ok": False, "text": "", "error": "empty path"}

    if _is_windows_host_path(target) and os.name != "nt":
        result = _host_read_file(target)
        data = result.get("data", {}) if isinstance(result, dict) else {}
        if not result.get("ok") or not data.get("ok", result.get("ok")):
            return {
                "ok": False,
                "text": "",
                "error": str(data.get("error", "Host bridge read failed")).strip() or "Host bridge read failed",
                "bridge_url": result.get("bridge_url", ""),
            }
        try:
            raw = base64.b64decode(str(data.get("content_base64", "")).encode("ascii"))
        except Exception as exc:
            return {"ok": False, "text": "", "error": f"Invalid host bridge payload: {exc}"}
        return {
            "ok": True,
            "text": raw.decode("utf-8", errors="replace"),
            "bridge_url": result.get("bridge_url", ""),
        }

    if os.name == "nt" and target.startswith("/"):
        for candidate in _fallback_local_candidates(target):
            if candidate.exists():
                try:
                    return {"ok": True, "text": candidate.read_text(encoding="utf-8")}
                except Exception as exc:
                    return {"ok": False, "text": "", "error": f"Failed to read fallback {candidate}: {exc}"}
        return {"ok": False, "text": "", "error": f"POSIX path not accessible on Windows: {target}"}

    path = _resolve_path(target)
    if not path.exists():
        return {"ok": False, "text": "", "error": f"File not found: {path}"}
    try:
        return {"ok": True, "text": path.read_text(encoding="utf-8")}
    except Exception as exc:
        return {"ok": False, "text": "", "error": f"Failed to read {path}: {exc}"}


def _load_text_if_exists(raw_path: str, warnings: list[str], label: str) -> str:
    target = str(raw_path or "").strip()
    if not target:
        return ""
    result = _read_text_result(target)
    if result.get("ok"):
        return str(result.get("text", ""))
    warnings.append(f"无法读取{label}: {target} ({result.get('error', 'unknown error')})")
    return ""


def _load_json_if_exists(raw_path: str, warnings: list[str], label: str) -> Any:
    text = _load_text_if_exists(raw_path, warnings, label)
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception as exc:
        warnings.append(f"无法解析{label} JSON: {raw_path} ({exc})")
        return None


def _load_json_quiet(raw_path: str) -> Any:
    result = _read_text_result(raw_path)
    if not result.get("ok"):
        return None
    text = str(result.get("text", ""))
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _unwrap_writing_input(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    current = dict(payload)
    visited: set[int] = set()
    while isinstance(current.get("writing_input"), dict) and id(current) not in visited:
        visited.add(id(current))
        nested = current.get("writing_input")
        if not isinstance(nested, dict):
            break
        current = dict(nested)
    return current


def _reference_lines_from_payload(payload: dict[str, Any], revision_request: str) -> str:
    references = payload.get("included_papers") or payload.get("references") or []
    lines: list[str] = []
    for index, paper in enumerate(references, start=1):
        if isinstance(paper, dict):
            authors = str(paper.get("authors", "")).strip()
            title = str(paper.get("title", "")).strip() or "Untitled"
            year = str(paper.get("year", "")).strip()
            citekey = str(paper.get("citekey", "")).strip()
            note_path = str(paper.get("relative_note_path", "")).strip()
            summary = str(paper.get("one_sentence_summary", "")).strip()
            label = f"[[{note_path}|{citekey or title}]]" if note_path else (citekey or title)
            if _GBT_RE.search(revision_request):
                body = " ".join(part for part in [authors, title, year] if part).strip() or title
                if summary:
                    body = f"{body}. {summary}"
                lines.append(f"[{index}] {body}")
            else:
                detail = f"{title} ({year})" if year else title
                if summary:
                    detail = f"{detail}: {summary}"
                lines.append(f"- {label} - {detail}")
        else:
            lines.append(f"- {paper}")
    return "\n".join(lines).strip() or "- 暂无可追溯参考文献。"


def _replace_reference_section(markdown: str, references_block: str) -> str:
    if not references_block.strip():
        return markdown
    pattern = re.compile(r"(?ms)^## 参考文献\s*\n.*$")
    replacement = f"## 参考文献\n{references_block}\n"
    if pattern.search(markdown):
        return pattern.sub(replacement, markdown)
    return markdown.rstrip() + "\n\n" + replacement


def _apply_revision_request(markdown: str, revision_request: str, payload: dict[str, Any]) -> str:
    rewritten = markdown.strip()
    if _ACADEMIC_STYLE_RE.search(revision_request):
        rewritten = _INFO_CALLOUT_RE.sub("", rewritten).strip()
    references_block = _reference_lines_from_payload(payload, revision_request)
    rewritten = _replace_reference_section(rewritten, references_block)
    return rewritten.strip() + "\n"


def _render_from_evidence(topic: str, review_note_path: str, writing_input: dict[str, Any], warnings: list[str]) -> str:
    if not writing_input:
        return ""
    try:
        render_review_draft = _load_review_renderer()
    except Exception as exc:
        warnings.append(f"无法复用综述草稿渲染器，改为使用现有正文: {exc}")
        return ""

    export_hint = str(
        writing_input.get("source_export_json", "")
        or writing_input.get("review_note_path", "")
        or review_note_path
    ).strip()
    export_path = _resolve_path(export_hint) if export_hint and not _is_windows_host_path(export_hint) else Path(str(review_note_path))
    pdf_stats = writing_input.get("pdf_stats", {}) if isinstance(writing_input.get("pdf_stats"), dict) else {}

    try:
        return str(
            render_review_draft(
                topic=topic,
                export_path=export_path,
                writing_input=writing_input,
                pdf_stats=pdf_stats,
            )
        ).strip()
    except Exception as exc:
        warnings.append(f"基于证据重建综述草稿失败，改为使用现有正文: {exc}")
        return ""


def _persist_rewrite_payload(topic: str, payload: dict[str, Any], markdown: str, artifacts_dir: str = "") -> tuple[str, str]:
    research_data_dir = Path(str(artifacts_dir or "").strip()) if str(artifacts_dir or "").strip() else (Path.cwd() / "research_data")
    research_data_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(topic, "review-rewrite")
    rewrite_input_path = research_data_dir / f"{slug}-review-rewrite-input.json"
    rewrite_input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rewrite_draft_path = research_data_dir / f"{slug}-review-rewrite-draft.md"
    rewrite_draft_path.write_text(markdown, encoding="utf-8")
    return str(rewrite_input_path), str(rewrite_draft_path)


def _infer_filename_style(note_path: str, frontmatter: dict[str, Any]) -> str:
    existing = str(frontmatter.get("filename_style", "")).strip().lower()
    if existing in {"title", "title-review"}:
        return existing
    return "title-review" if str(note_path).replace("\\", "/").endswith(" - review.md") else "title"


def _infer_review_style(frontmatter: dict[str, Any]) -> str:
    existing = str(frontmatter.get("review_style", "")).strip().lower()
    return existing if existing in {"survey_cn", "legacy_materials"} else "survey_cn"


@tool
def obsidian_rewrite_materials_review_note(
    review_note_path: str = "",
    topic: str = "",
    category: str = "",
    revision_request: str = "",
    vault_dir: str = "",
    overwrite_existing: bool = True,
) -> dict:
    """Rewrite an existing Obsidian review note using the latest local evidence bundle."""
    logger.info(
        "[obsidian_rewrite_materials_review_note] review_note_path=%r topic=%r vault_dir=%r overwrite_existing=%s",
        review_note_path,
        topic,
        vault_dir,
        overwrite_existing,
    )

    revision_text = _clean_text(revision_request)
    if not revision_text:
        return {"ok": False, "error": "revision_request is required"}

    try:
        resolved_note_path = _infer_review_note_path(review_note_path, topic, vault_dir, category)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    note_read = _read_text_result(resolved_note_path)
    if not note_read.get("ok"):
        return {
            "ok": False,
            "error": f"Review note not found or unreadable: {resolved_note_path} ({note_read.get('error', 'unknown error')})",
        }

    note_text = str(note_read.get("text", ""))
    frontmatter, current_body = _split_frontmatter(note_text)
    embedded_frontmatter, current_body = _extract_embedded_frontmatter_from_body(current_body)
    frontmatter = _merge_frontmatter(frontmatter, embedded_frontmatter)
    resolved_topic = (
        str(topic or "").strip()
        or str(frontmatter.get("topic", "")).strip()
        or str(frontmatter.get("title", "")).strip()
        or re.sub(r"\s*-\s*review$", "", Path(str(resolved_note_path)).stem, flags=re.IGNORECASE)
    )

    effective_vault_dir = str(vault_dir or "").strip() or _infer_vault_dir_from_note_path(resolved_note_path)
    review_input_path = str(frontmatter.get("review_input_path", "")).strip()
    review_draft_path = str(frontmatter.get("review_draft_path", "")).strip()

    warnings: list[str] = []
    loaded_review_input = _load_json_if_exists(review_input_path, warnings, "review_input_path")
    payload_frontmatter = (
        loaded_review_input.get("current_frontmatter", {})
        if isinstance(loaded_review_input, dict) and isinstance(loaded_review_input.get("current_frontmatter"), dict)
        else {}
    )
    frontmatter = _merge_frontmatter(frontmatter, payload_frontmatter)
    source_writing_input_path = str(
        _coalesce_first_nonempty(
            frontmatter.get("source_writing_input_path", ""),
            payload_frontmatter.get("source_writing_input_path", ""),
            loaded_review_input.get("source_writing_input_path", "") if isinstance(loaded_review_input, dict) else "",
        )
    ).strip()
    writing_input = _unwrap_writing_input(loaded_review_input)
    if not _has_usable_writing_input(writing_input):
        for candidate in _source_writing_input_candidates(
            topic=resolved_topic,
            review_input_path=review_input_path,
            source_writing_input_path=source_writing_input_path,
            loaded_review_input=loaded_review_input,
            frontmatter=frontmatter,
            payload_frontmatter=payload_frontmatter,
        ):
            candidate_payload = _load_json_quiet(candidate)
            candidate_frontmatter = (
                candidate_payload.get("current_frontmatter", {})
                if isinstance(candidate_payload, dict) and isinstance(candidate_payload.get("current_frontmatter"), dict)
                else {}
            )
            candidate_writing_input = _unwrap_writing_input(candidate_payload)
            if _has_usable_writing_input(candidate_writing_input):
                source_writing_input_path = candidate
                frontmatter = _merge_frontmatter(frontmatter, candidate_frontmatter)
                payload_frontmatter = _merge_frontmatter(payload_frontmatter, candidate_frontmatter)
                writing_input = candidate_writing_input
                break
        if not _has_usable_writing_input(writing_input):
            warnings.append(
                "Unable to resolve a usable source_writing_input_path; rewrite will rely on the current note body."
            )
    resolved_category = (
        str(category or "").strip()
        or str(frontmatter.get("category", "")).strip()
        or str(payload_frontmatter.get("category", "")).strip()
        or str(writing_input.get("category", "") if isinstance(writing_input, dict) else "").strip()
    )
    review_bundle_path = str(
        _coalesce_first_nonempty(
            frontmatter.get("review_bundle_path", ""),
            payload_frontmatter.get("review_bundle_path", ""),
            writing_input.get("bundle_path", "") if isinstance(writing_input, dict) else "",
            writing_input.get("review_bundle_path", "") if isinstance(writing_input, dict) else "",
        )
    ).strip()
    source_export_json = str(
        _coalesce_first_nonempty(
            frontmatter.get("source_export_json", ""),
            payload_frontmatter.get("source_export_json", ""),
            writing_input.get("source_export_json", "") if isinstance(writing_input, dict) else "",
        )
    ).strip()
    existing_draft = _load_text_if_exists(review_draft_path, warnings, "review_draft_path")
    _ = _load_json_if_exists(review_bundle_path, warnings, "review_bundle_path")

    rewrite_source_markdown = _render_from_evidence(resolved_topic, resolved_note_path, writing_input, warnings)
    if not rewrite_source_markdown:
        rewrite_source_markdown = existing_draft.strip() or current_body.strip()
    if not rewrite_source_markdown:
        return {
            "ok": False,
            "error": f"Unable to build rewrite source for review note: {resolved_note_path}",
            "review_note_path": resolved_note_path,
            "warnings": warnings,
        }

    skill_rewriter = _load_skill_rewriter()
    polish_result = skill_rewriter(
        topic=resolved_topic,
        draft_markdown=rewrite_source_markdown,
        writing_input=writing_input,
        revision_request=revision_text,
        current_body=current_body.strip(),
        review_note_path=resolved_note_path,
    )
    if not isinstance(polish_result, dict) or not polish_result.get("ok"):
        return {
            "ok": False,
            "error": (
                polish_result.get("error", "Failed to run skill-driven rewrite")
                if isinstance(polish_result, dict)
                else "Failed to run skill-driven rewrite"
            ),
            "review_note_path": resolved_note_path,
            "effective_vault_dir": effective_vault_dir,
            "used_skill_pipeline": list(_REQUIRED_LOCAL_SKILLS),
            "warnings": warnings,
            "required_skills": list(_REQUIRED_LOCAL_SKILLS),
            "read_skills": polish_result.get("read_skills", []) if isinstance(polish_result, dict) else [],
            "missing_required_skills": (
                polish_result.get("missing_required_skills", list(_REQUIRED_LOCAL_SKILLS))
                if isinstance(polish_result, dict)
                else list(_REQUIRED_LOCAL_SKILLS)
            ),
        }
    rewritten_markdown = str(polish_result.get("markdown", "")).strip()
    _, rewritten_markdown = _split_frontmatter(rewritten_markdown)
    _, rewritten_markdown = _extract_embedded_frontmatter_from_body(rewritten_markdown)
    rewritten_markdown = rewritten_markdown.strip()
    read_skills = polish_result.get("read_skills", [])
    missing_required_skills = polish_result.get("missing_required_skills", [])

    rewrite_payload = {
        "topic": resolved_topic,
        "category": resolved_category,
        "revision_request": revision_text,
        "review_note_path": resolved_note_path,
        "review_input_path": review_input_path,
        "review_draft_path": review_draft_path,
        "review_bundle_path": review_bundle_path,
        "source_export_json": source_export_json,
        "source_writing_input_path": source_writing_input_path or review_input_path,
        "effective_vault_dir": effective_vault_dir,
        "current_frontmatter": frontmatter,
        "current_body": current_body.strip(),
        "writing_input": writing_input,
        "used_skill_pipeline": list(_REQUIRED_LOCAL_SKILLS),
        "required_skills": list(_REQUIRED_LOCAL_SKILLS),
        "read_skills": read_skills,
        "missing_required_skills": missing_required_skills,
    }
    rewrite_input_path, rewrite_draft_output_path = _persist_rewrite_payload(
        topic=resolved_topic,
        payload=rewrite_payload,
        markdown=rewritten_markdown,
        artifacts_dir=str(Path(review_bundle_path).parent) if review_bundle_path else "",
    )

    review_metadata = dict(frontmatter)
    if not review_metadata.get("keywords") and isinstance(writing_input, dict):
        review_metadata["keywords"] = writing_input.get("keywords", [])
    if not review_metadata.get("tags"):
        review_metadata["tags"] = payload_frontmatter.get("tags", []) or ["materials-review", "zotero-review-agent", "zotero-import"]
    if isinstance(writing_input, dict):
        included_count = len(writing_input.get("included_papers", []) or []) or (
            len(writing_input.get("core_papers", []) or []) + len(writing_input.get("boundary_papers", []) or [])
        )
        boundary_count = len(writing_input.get("boundary_papers", []) or [])
        noise_count = len(writing_input.get("noise_papers", []) or [])
        if int(review_metadata.get("included_paper_count", 0) or 0) <= 0 and included_count > 0:
            review_metadata["included_paper_count"] = included_count
        if int(review_metadata.get("boundary_paper_count", 0) or 0) <= 0 and boundary_count > 0:
            review_metadata["boundary_paper_count"] = boundary_count
        if int(review_metadata.get("noise_paper_count", 0) or 0) <= 0 and noise_count > 0:
            review_metadata["noise_paper_count"] = noise_count
    if not review_metadata.get("pdf_stats") and isinstance(writing_input, dict):
        review_metadata["pdf_stats"] = writing_input.get("pdf_stats", {})
    review_metadata.update(
        {
            "title": review_metadata.get("title", resolved_topic) or resolved_topic,
            "topic": resolved_topic,
            "category": resolved_category,
            "writing_pass": "scientific-writing",
            "skill_pipeline": list(_REQUIRED_LOCAL_SKILLS),
            "required_skills": list(_REQUIRED_LOCAL_SKILLS),
            "read_skills": read_skills,
            "missing_required_skills": missing_required_skills,
            "review_input_path": rewrite_input_path,
            "review_draft_path": rewrite_draft_output_path,
            "source_writing_input_path": source_writing_input_path or review_input_path,
            "review_bundle_path": review_bundle_path,
        }
    )
    if source_export_json:
        review_metadata["source_export_json"] = source_export_json

    writer_tool = _load_writer_tool()
    write_result = writer_tool.invoke(
        {
            "note_type": "review",
            "title": resolved_topic,
            "content": rewritten_markdown,
            "metadata_json": json.dumps(review_metadata, ensure_ascii=False),
            "project_name": resolved_topic,
            "category": resolved_category,
            "vault_dir": effective_vault_dir,
            "overwrite": overwrite_existing,
            "review_style": _infer_review_style(frontmatter),
            "filename_style": _infer_filename_style(resolved_note_path, frontmatter),
            "conflict_mode": "error",
        }
    )

    if not write_result.get("ok"):
        return {
            "ok": False,
            "error": write_result.get("error", "Failed to rewrite review note"),
            "review_note_path": resolved_note_path,
            "effective_vault_dir": write_result.get("effective_vault_dir", effective_vault_dir),
            "used_skill_pipeline": list(_REQUIRED_LOCAL_SKILLS),
            "warnings": warnings,
            "requested_vault_dir": write_result.get("requested_vault_dir", effective_vault_dir),
            "effective_vault_source": write_result.get("effective_vault_source", ""),
            "fell_back_to_default_vault": write_result.get("fell_back_to_default_vault", False),
            "vault_match_status": write_result.get("vault_match_status", "exact"),
            "required_skills": write_result.get("required_skills", list(_REQUIRED_LOCAL_SKILLS)),
            "read_skills": write_result.get("read_skills", []),
            "missing_required_skills": write_result.get("missing_required_skills", []),
        }

    return {
        "ok": True,
        "topic": resolved_topic,
        "category": resolved_category,
        "review_note_path": str(write_result.get("note_path", write_result.get("relative_note_path", resolved_note_path))).strip(),
        "effective_vault_dir": write_result.get("effective_vault_dir", effective_vault_dir),
        "effective_vault_source": write_result.get("effective_vault_source", ""),
        "requested_vault_dir": write_result.get("requested_vault_dir", effective_vault_dir),
        "fell_back_to_default_vault": write_result.get("fell_back_to_default_vault", False),
        "vault_match_status": write_result.get("vault_match_status", "exact"),
        "used_skill_pipeline": list(_REQUIRED_LOCAL_SKILLS),
        "review_input_path": rewrite_input_path,
        "review_draft_path": rewrite_draft_output_path,
        "review_bundle_path": review_bundle_path,
        "warnings": warnings,
        "required_skills": write_result.get("required_skills", list(_REQUIRED_LOCAL_SKILLS)),
        "read_skills": write_result.get("read_skills", []),
        "missing_required_skills": write_result.get("missing_required_skills", []),
    }
