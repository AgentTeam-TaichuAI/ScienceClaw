import json
import logging
import ntpath
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Obsidian",
    "subcategory": "Authoring",
    "tags": ["obsidian", "materials", "notes", "knowledge-base"],
}

_DEFAULT_VAULT_DIR = Path(os.environ.get("OBSIDIAN_VAULT_DIR", "/home/scienceclaw/obsidian_vault"))
_VALID_NOTE_TYPES = {"literature", "review", "project"}
_VALID_REVIEW_STYLES = {"legacy_materials", "survey_cn"}
_VALID_FILENAME_STYLES = {"title-review", "title"}
_VALID_CONFLICT_MODES = {"error", "timestamp"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_DEFAULT_BRIDGE_CANDIDATES = [
    "http://127.0.0.1:8765",
    "http://host.docker.internal:8765",
]
_SURVEY_CN_HEADINGS = [
    "## 摘要",
    "## 关键词",
    "## 引言",
    "## 技术基础与发展脉络",
    "## 主要研究方向",
    "## 代表性工作比较与讨论",
    "## 挑战与争议",
    "## 未来趋势与机会",
    "## 结论",
    "## 参考文献",
]


def _is_windows_host_path(raw_path: str) -> bool:
    return bool(_WINDOWS_DRIVE_RE.match(str(raw_path or "").strip()))


def _normalized_path_key(raw_path: str) -> str:
    raw = str(raw_path or "").strip()
    if not raw:
        return ""
    if _is_windows_host_path(raw):
        return f"windows:{ntpath.normcase(ntpath.normpath(raw))}"
    try:
        return f"posix:{Path(raw).expanduser().resolve(strict=False)}"
    except Exception:
        return f"raw:{raw.replace('\\', '/')}"


def _vault_match_status(requested_vault_dir: str, effective_vault_dir: str) -> str:
    requested = str(requested_vault_dir or "").strip()
    effective = str(effective_vault_dir or "").strip()
    if not requested:
        return "exact"
    if not effective:
        return "fallback_other_path"
    if requested == effective:
        return "exact"
    if _normalized_path_key(requested) == _normalized_path_key(effective):
        return "normalized_same_path"
    return "fallback_other_path"


def _vault_report(requested_vault_dir: str, effective_vault_dir: str, vault_source: str) -> dict[str, Any]:
    requested = str(requested_vault_dir or "").strip()
    effective = str(effective_vault_dir or "").strip()
    source = str(vault_source or "").strip() or ("configured" if requested else "env_default")
    match_status = _vault_match_status(requested, effective)
    fell_back = match_status == "fallback_other_path"
    return {
        "requested_vault_dir": requested,
        "effective_vault_dir": effective,
        "effective_vault_source": source,
        "fell_back_to_default_vault": fell_back,
        "vault_match_status": match_status,
    }


def _resolve_runtime_paths(vault_dir: str = "", category: str = "") -> dict[str, Any]:
    configured = str(vault_dir or "").strip()
    if configured:
        if os.name != "nt" and _is_windows_host_path(configured):
            vault_root = _DEFAULT_VAULT_DIR
            source = "fallback_default_mount"
        else:
            candidate = Path(configured).expanduser()
            vault_root = candidate if candidate.is_absolute() else (Path.cwd() / candidate)
            source = "configured"
    else:
        vault_root = _DEFAULT_VAULT_DIR
        source = "env_default"

    materials_root = vault_root / "Research" / "Materials"
    note_dirs = {
        "literature": materials_root / "Literature Notes",
        "review": materials_root / "Review Notes",
        "project": materials_root / "Projects",
    }
    figures_dir = materials_root / "Figures"
    datasets_dir = materials_root / "Datasets"
    category_dir = _category_dir_name(category, {})
    category_dirs = {}
    if category_dir:
        category_dirs = {
            "literature": note_dirs["literature"] / category_dir,
            "review": note_dirs["review"] / category_dir,
            "project": note_dirs["project"] / category_dir,
            "figures": figures_dir / category_dir,
            "datasets": datasets_dir / category_dir,
        }
    return {
        "vault_dir": vault_root,
        "materials_root": materials_root,
        "note_dirs": note_dirs,
        "figures_dir": figures_dir,
        "datasets_dir": datasets_dir,
        "templates_dir": materials_root / "Templates",
        "category": str(category or "").strip(),
        "category_dir": category_dir,
        "category_dirs": category_dirs,
        "vault_source": source,
    }


def _bridge_candidates() -> list[str]:
    configured = (os.environ.get("OBSIDIAN_HOST_BRIDGE_URL", "") or "").strip()
    candidates: list[str] = []
    if configured:
        candidates.append(configured.rstrip("/"))
    for candidate in _DEFAULT_BRIDGE_CANDIDATES:
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _bridge_headers() -> dict[str, str]:
    return {
        "X-Bridge-Token": os.environ.get("OBSIDIAN_HOST_BRIDGE_TOKEN", "scienceclaw-local-bridge"),
    }


def _should_use_host_bridge(vault_dir: str) -> bool:
    configured = str(vault_dir or "").strip()
    return bool(configured) and os.name != "nt" and _is_windows_host_path(configured)


def _bridge_fallback_reason(result: dict[str, Any]) -> str:
    data = result.get("data", {}) if isinstance(result, dict) else {}
    error = str(data.get("error", "")).strip()
    if error:
        return error
    return str(result.get("error", "")).strip()


def _should_fallback_to_mount(bridge_result: dict[str, Any]) -> bool:
    reason = _bridge_fallback_reason(bridge_result).lower()
    if not reason:
        return False
    fallback_markers = (
        "invalid bridge token",
        "host bridge unavailable",
        "connection refused",
        "name or service not known",
        "timed out",
        "sc_host_read_roots",
        "unauthorized",
    )
    return any(marker in reason for marker in fallback_markers)


def _bridge_request(method: str, route: str, payload: dict[str, Any], timeout: float = 20.0) -> dict[str, Any]:
    last_error: Exception | None = None
    for base_url in _bridge_candidates():
        try:
            response = httpx.request(
                method.upper(),
                f"{base_url}{route}",
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


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if not value.strip():
            return []
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value.strip()]
    return [str(value).strip()]


def _normalize_keywords(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if any(sep in text for sep in [",", "，", ";", "；"]):
            return [part.strip() for part in re.split(r"[,，;；]", text) if part.strip()]
        return [text]
    return []


def _skill_usage_report(metadata: dict[str, Any]) -> dict[str, list[str]]:
    required_skills = _normalize_list(metadata.get("required_skills"))
    read_skills = _normalize_list(metadata.get("read_skills"))
    missing_required_skills = _normalize_list(metadata.get("missing_required_skills"))
    if required_skills and not missing_required_skills:
        missing_required_skills = [skill for skill in required_skills if skill not in set(read_skills)]
    return {
        "required_skills": required_skills,
        "read_skills": read_skills,
        "missing_required_skills": missing_required_skills,
    }


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _slugify(text: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-_").lower()
    return slug or fallback


def _sanitize_file_component(text: str, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n]+', " ", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:120] or fallback


def _first_nonempty_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = str(item or "").strip()
            if text:
                return text
        return ""
    return str(value or "").strip()


def _metadata_category(metadata: dict[str, Any]) -> str:
    for key in ("category", "classification", "zotero_category", "topic_category"):
        text = _normalize_category_candidate(_first_nonempty_text(metadata.get(key, "")), metadata)
        if text:
            return text
    return ""


def _metadata_category_fallback(metadata: dict[str, Any]) -> str:
    for key in ("topic", "project_name", "project", "title"):
        text = _first_nonempty_text(metadata.get(key, ""))
        if text:
            return text
    return ""


def _normalize_category_candidate(category: str, metadata: dict[str, Any]) -> str:
    text = str(category or "").strip()
    if not text:
        return ""
    normalized = _sanitize_file_component(text, "").lower()
    if normalized in {"material", "materials"}:
        fallback = _metadata_category_fallback(metadata)
        fallback_normalized = _sanitize_file_component(fallback, "").lower()
        if fallback and fallback_normalized and fallback_normalized != normalized:
            return fallback
    return text


def _resolve_category_value(category: str, metadata: dict[str, Any]) -> str:
    explicit = _normalize_category_candidate(str(category or "").strip(), metadata)
    if explicit:
        return explicit
    return _metadata_category(metadata)


def _category_dir_name(category: str, metadata: dict[str, Any]) -> str:
    resolved = _resolve_category_value(category, metadata)
    if not resolved:
        return ""
    return _sanitize_file_component(resolved, "")


def _to_rel_path(path: Path, vault_dir: Path) -> str:
    return path.relative_to(vault_dir).as_posix()


def _sanitize_created_dirs(values: Any) -> list[str]:
    allowed_roots = {
        "Research/Materials",
        "Research/Materials/Literature Notes",
        "Research/Materials/Review Notes",
        "Research/Materials/Templates",
    }
    cleaned: list[str] = []
    for value in values or []:
        text = str(value or "").replace("\\", "/").strip().strip("/")
        if not text:
            continue
        if (
            text in allowed_roots
            or text.startswith("Research/Materials/Literature Notes/")
            or text.startswith("Research/Materials/Review Notes/")
        ) and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _sanitize_created_templates(values: Any) -> list[str]:
    allowed = {
        "Research/Materials/Templates/literature-note.md",
        "Research/Materials/Templates/review-note.md",
    }
    cleaned: list[str] = []
    for value in values or []:
        text = str(value or "").replace("\\", "/").strip().strip("/")
        if text in allowed and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _format_link(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if raw.startswith("[[") or raw.startswith("![["):
        return raw
    if raw.startswith("http://") or raw.startswith("https://"):
        return f"- [{raw}]({raw})"

    suffix = Path(raw).suffix.lower()
    normalized = raw.replace("\\", "/")
    if normalized.startswith("Research/Materials/"):
        return f"- ![[{normalized}]]" if suffix in _IMAGE_SUFFIXES else f"- [[{normalized}]]"
    if suffix in _IMAGE_SUFFIXES:
        return f"- ![[{normalized}]]"
    if suffix:
        return f"- [[{normalized}]]"
    return f"- {raw}"


def _render_bullets(values: list[str], empty_message: str) -> str:
    if not values:
        return f"- {empty_message}"
    return "\n".join(f"- {value}" for value in values)


def _render_link_block(values: list[str], empty_message: str) -> str:
    lines = [_format_link(value) for value in values]
    lines = [line for line in lines if line]
    if not lines:
        return f"- {empty_message}"
    return "\n".join(lines)


def _render_cpp_extracts(rows: list[Any]) -> str:
    if not rows:
        return "- No structured composition-processing-microstructure-property extracts yet."

    rendered: list[str] = []
    for index, row in enumerate(rows, start=1):
        if isinstance(row, dict):
            composition = row.get("composition", "")
            processing = row.get("processing", "")
            microstructure = row.get("microstructure", "")
            property_name = row.get("property", row.get("property_name", ""))
            value = row.get("value", "")
            unit = row.get("unit", "")
            rendered.append(
                f"- Extract {index}: composition={composition or 'n/a'}; "
                f"processing={processing or 'n/a'}; microstructure={microstructure or 'n/a'}; "
                f"property={property_name or 'n/a'}; value={value or 'n/a'} {unit}".rstrip()
            )
        else:
            rendered.append(f"- Extract {index}: {row}")
    return "\n".join(rendered)


def _render_evidence(values: list[Any]) -> str:
    if not values:
        return "- Evidence pages not recorded yet."

    rendered: list[str] = []
    for value in values:
        if isinstance(value, dict):
            page = value.get("page", value.get("page_label", "n/a"))
            quote = str(value.get("quote", "")).strip()
            note = str(value.get("note", "")).strip()
            detail = "; ".join(part for part in [quote, note] if part)
            rendered.append(f"- Page {page}: {detail}" if detail else f"- Page {page}")
        else:
            rendered.append(f"- {value}")
    return "\n".join(rendered)


def _render_reference_block(values: list[Any], empty_message: str) -> str:
    if not values:
        return f"- {empty_message}"

    rendered: list[str] = []
    for value in values:
        if isinstance(value, dict):
            citekey = str(value.get("citekey", "")).strip()
            title = str(value.get("title", "")).strip() or citekey or "Untitled reference"
            year = str(value.get("year", "")).strip()
            note_path = str(value.get("relative_note_path", "")).strip()
            summary = str(value.get("one_sentence_summary", "")).strip()
            prefix = f"{title} ({year})" if year else title
            line = f"- [[{note_path}]] - {prefix}" if note_path else f"- {prefix}"
            if summary:
                line = f"{line}: {summary}"
            rendered.append(line)
            continue
        text = str(value).strip()
        if text:
            rendered.append(_format_link(text))

    rendered = [line for line in rendered if line]
    if not rendered:
        return f"- {empty_message}"
    return "\n".join(rendered)


def _section_text(*values: Any, fallback: str) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return fallback


def _render_kv_lines(pairs: list[tuple[str, Any]]) -> str:
    lines: list[str] = []
    for label, value in pairs:
        text = str(value or "").strip()
        if text:
            lines.append(f"- {label}: {text}")
    return "\n".join(lines)


def _append_section(blocks: list[str], title: str, body: str) -> None:
    text = _clean_text(body)
    if not text:
        return
    blocks.extend([f"## {title}", text, ""])


def _has_survey_cn_structure(content: str) -> bool:
    cleaned = _clean_text(content)
    if not cleaned:
        return False
    hits = sum(1 for heading in _SURVEY_CN_HEADINGS if heading in cleaned)
    if hits >= 2:
        return True

    # Accept already-structured survey drafts that use custom numbered H2 headings
    # instead of the fixed template section names.
    h2_hits = re.findall(r"(?m)^##\s+.+$", cleaned)
    if len(h2_hits) >= 3:
        return True
    if cleaned.startswith("# ") and len(h2_hits) >= 2:
        return True
    return False


def _append_h1_if_missing(title: str, body: str) -> str:
    cleaned = body.lstrip()
    if cleaned.startswith("# "):
        return body.strip()
    return f"# {title}\n\n{body.strip()}"


def _template_content(template_name: str) -> str:
    if template_name == "literature":
        return """---
title: "{{title}}"
authors: []
year:
doi: ""
citekey: ""
zotero_key: ""
tags: []
alloy_family: ""
property_focus: ""
---

# {{title}}

## Basic Information

## One-Sentence Conclusion

## 中文速览

## Composition-Processing-Microstructure-Property Extracts

## Key Figures

## Evidence Pages

## Related Projects

## AI Notes
"""

    if template_name == "review":
        return """---
title: "{{title}}"
topic: "{{topic}}"
keywords: []
review_style: "survey_cn"
tags: ["materials-review"]
---

# {{title}}

## 摘要

## 关键词

## 引言

## 技术基础与发展脉络

## 主要研究方向

## 代表性工作比较与讨论

## 挑战与争议

## 未来趋势与机会

## 结论

## 参考文献
"""

    return """---
title: "{{title}}"
project: "{{project}}"
tags: ["materials-project"]
---

# {{title}}

## Research Goal

## Candidate Alloy and Process Hypotheses

## Data Sources

## Figure Index

## Current Conclusions

## Open Questions

## Next Experiments
"""


def _ensure_materials_layout(runtime_paths: dict[str, Any], overwrite_templates: bool) -> dict[str, list[str]]:
    vault_dir = runtime_paths["vault_dir"]
    materials_root = runtime_paths["materials_root"]
    note_dirs = runtime_paths["note_dirs"]
    figures_dir = runtime_paths["figures_dir"]
    datasets_dir = runtime_paths["datasets_dir"]
    templates_dir = runtime_paths["templates_dir"]
    category_dirs = runtime_paths.get("category_dirs", {}) or {}
    created_dirs: list[str] = []
    created_templates: list[str] = []

    for directory in [materials_root, *note_dirs.values(), figures_dir, datasets_dir, templates_dir, *category_dirs.values()]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs.append(_to_rel_path(directory, vault_dir))

    template_paths = {
        "literature": templates_dir / "Literature Note Template.md",
        "review": templates_dir / "Review Note Template.md",
        "project": templates_dir / "Project Note Template.md",
    }
    for template_name, template_path in template_paths.items():
        if overwrite_templates or not template_path.exists():
            template_path.write_text(_template_content(template_name), encoding="utf-8")
            created_templates.append(_to_rel_path(template_path, vault_dir))

    return {"created_dirs": created_dirs, "created_templates": created_templates}


def _frontmatter(
    note_type: str,
    title: str,
    metadata: dict[str, Any],
    relative_note_path: str,
    review_style: str,
    filename_style: str,
) -> str:
    frontmatter: dict[str, Any] = {
        "title": metadata.get("title", title),
        "authors": _normalize_list(metadata.get("authors")),
        "year": metadata.get("year", ""),
        "doi": metadata.get("doi", ""),
        "citekey": metadata.get("citekey", ""),
        "zotero_key": metadata.get("zotero_key", ""),
        "tags": _normalize_list(metadata.get("tags")),
        "alloy_family": metadata.get("alloy_family", ""),
        "property_focus": metadata.get("property_focus", ""),
        "note_type": note_type,
        "materials_root": "Research/Materials",
        "generated_by": "ScienceClaw",
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "vault_path": relative_note_path,
    }
    resolved_category = _metadata_category(metadata)
    if resolved_category:
        frontmatter["category"] = resolved_category

    if note_type == "review":
        frontmatter["topic"] = metadata.get("topic", title)
        frontmatter["keywords"] = _normalize_keywords(metadata.get("keywords"))
        frontmatter["review_style"] = review_style
        frontmatter["filename_style"] = filename_style
        if metadata.get("review_bundle_path"):
            frontmatter["review_bundle_path"] = metadata.get("review_bundle_path")
        if metadata.get("source_export_json"):
            frontmatter["source_export_json"] = metadata.get("source_export_json")
        if metadata.get("writing_pass"):
            frontmatter["writing_pass"] = metadata.get("writing_pass")
        if metadata.get("skill_pipeline"):
            frontmatter["skill_pipeline"] = _normalize_list(metadata.get("skill_pipeline"))
        if metadata.get("review_input_path"):
            frontmatter["review_input_path"] = metadata.get("review_input_path")
        if metadata.get("review_draft_path"):
            frontmatter["review_draft_path"] = metadata.get("review_draft_path")
        if metadata.get("source_writing_input_path"):
            frontmatter["source_writing_input_path"] = metadata.get("source_writing_input_path")
        for count_key in ("included_paper_count", "boundary_paper_count", "noise_paper_count"):
            if count_key in metadata:
                frontmatter[count_key] = metadata.get(count_key)
        if metadata.get("pdf_stats"):
            frontmatter["pdf_stats"] = metadata.get("pdf_stats")

    return yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()


def _render_literature_note(title: str, metadata: dict[str, Any], content: str) -> str:
    short_summary = str(metadata.get("one_sentence_summary", "")).strip() or "Pending summary."
    cn_overview = _section_text(
        metadata.get("cn_overview"),
        metadata.get("chinese_overview"),
        metadata.get("中文速览"),
        fallback="",
    )
    extracts = _render_cpp_extracts(metadata.get("composition_process_property", []))
    figures = _render_link_block(_normalize_list(metadata.get("key_figures")), "No figure links yet.")
    evidence = _render_evidence(metadata.get("evidence_pages", []))
    related_projects = _render_link_block(_normalize_list(metadata.get("project_links")), "No related project links yet.")
    ai_notes = content.strip() or "Pending AI analysis."

    cn_section = ""
    if cn_overview:
        cn_section = f"\n## 中文速览\n{cn_overview}\n"

    return f"""# {title}

## Basic Information
- Authors: {", ".join(_normalize_list(metadata.get("authors"))) or "Unknown"}
- Year: {metadata.get("year", "") or "Unknown"}
- DOI: {metadata.get("doi", "") or "Unknown"}
- Citekey: {metadata.get("citekey", "") or "Not available"}
- Zotero Key: {metadata.get("zotero_key", "") or "Not available"}
- Alloy Family: {metadata.get("alloy_family", "") or "Not specified"}
- Property Focus: {metadata.get("property_focus", "") or "Not specified"}

## One-Sentence Conclusion
{short_summary}{cn_section}
## Composition-Processing-Microstructure-Property Extracts
{extracts}

## Key Figures
{figures}

## Evidence Pages
{evidence}

## Related Projects
{related_projects}

## AI Notes
{ai_notes}
"""


def _render_review_note_legacy(title: str, metadata: dict[str, Any], content: str) -> str:
    return f"""# {title}

## Background
{content.strip() or str(metadata.get("background", "")).strip() or "Pending background synthesis."}

## Alloy System Classification
{_render_bullets(_normalize_list(metadata.get("alloy_classification")), "No alloy system classification yet.")}

## Processing Routes
{_render_bullets(_normalize_list(metadata.get("processing_routes")), "No processing routes summarized yet.")}

## Performance Comparison
{_render_bullets(_normalize_list(metadata.get("performance_comparison")), "No performance comparison summary yet.")}

## Consensus and Disputes
{_render_bullets(_normalize_list(metadata.get("consensus_and_disputes")), "No consensus/dispute notes yet.")}

## Opportunity Areas
{_render_bullets(_normalize_list(metadata.get("opportunity_areas")), "No opportunity areas recorded yet.")}

## Reference Index
{_render_link_block(_normalize_list(metadata.get("references")), "No reference index yet.")}
"""


def _render_review_note_survey_cn(title: str, metadata: dict[str, Any], content: str) -> str:
    if _has_survey_cn_structure(content):
        return _append_h1_if_missing(title, content)

    keywords = _normalize_keywords(metadata.get("keywords"))
    if not keywords:
        keywords = _normalize_keywords(metadata.get("keyword_list"))

    summary = _section_text(
        metadata.get("abstract"),
        metadata.get("summary"),
        metadata.get("executive_summary"),
        fallback=content.strip() or "待补充摘要。",
    )
    introduction = _section_text(
        metadata.get("introduction"),
        metadata.get("background"),
        fallback="待补充引言。",
    )
    foundations = _section_text(
        metadata.get("technical_foundations"),
        metadata.get("development_history"),
        metadata.get("timeline"),
        fallback="待补充技术基础与发展脉络。",
    )
    directions = _section_text(
        metadata.get("main_research_directions"),
        metadata.get("research_directions"),
        metadata.get("direction_summary"),
        fallback="待补充主要研究方向。",
    )
    comparison = _section_text(
        metadata.get("representative_comparison"),
        metadata.get("comparison_discussion"),
        metadata.get("performance_comparison"),
        fallback="待补充代表性工作比较与讨论。",
    )
    challenges = _section_text(
        metadata.get("challenges"),
        metadata.get("consensus_and_disputes"),
        fallback="待补充挑战与争议。",
    )
    future = _section_text(
        metadata.get("future_trends"),
        metadata.get("future_opportunities"),
        metadata.get("opportunity_areas"),
        fallback="待补充未来趋势与机会。",
    )
    conclusion = _section_text(
        metadata.get("conclusion"),
        metadata.get("closing_summary"),
        fallback="待补充结论。",
    )
    references = _render_reference_block(metadata.get("references", []), "待补充参考文献。")
    keyword_text = "；".join(keywords) if keywords else "待补充关键词。"

    return f"""# {title}

## 摘要
{summary}

## 关键词
{keyword_text}

## 引言
{introduction}

## 技术基础与发展脉络
{foundations}

## 主要研究方向
{directions}

## 代表性工作比较与讨论
{comparison}

## 挑战与争议
{challenges}

## 未来趋势与机会
{future}

## 结论
{conclusion}

## 参考文献
{references}
"""


def _render_project_note(title: str, metadata: dict[str, Any], content: str) -> str:
    return f"""# {title}

## Research Goal
{str(metadata.get("research_goal", "")).strip() or content.strip() or "Pending research goal."}

## Candidate Alloy and Process Hypotheses
{_render_bullets(_normalize_list(metadata.get("candidate_hypotheses")), "No candidate hypotheses yet.")}

## Data Sources
{_render_link_block(_normalize_list(metadata.get("data_sources")), "No data sources linked yet.")}

## Figure Index
{_render_link_block(_normalize_list(metadata.get("figure_links")), "No figure links yet.")}

## Current Conclusions
{_render_bullets(_normalize_list(metadata.get("current_conclusions")), "No conclusions recorded yet.")}

## Open Questions
{_render_bullets(_normalize_list(metadata.get("open_questions")), "No open questions recorded yet.")}

## Next Experiments
{_render_bullets(_normalize_list(metadata.get("next_experiments")), "No next-step experiments recorded yet.")}

## Dataset Links
{_render_link_block(_normalize_list(metadata.get("dataset_links")), "No dataset links yet.")}
"""


def _review_file_stem(title: str, metadata: dict[str, Any], project_name: str, filename_style: str) -> str:
    base = str(title).strip() or str(metadata.get("topic", "")).strip() or str(project_name or "").strip()
    base = _sanitize_file_component(base, "materials-topic")
    if filename_style == "title":
        return base
    topic = _sanitize_file_component(project_name or metadata.get("topic", "") or title, "materials-topic")
    return f"{topic} - review"


def _build_note_relative_path(
    note_type: str,
    title: str,
    metadata: dict[str, Any],
    project_name: str,
    filename_style: str,
    category: str,
) -> str:
    category_dir = _category_dir_name(category, metadata)
    if note_type == "literature":
        citekey = _sanitize_file_component(str(metadata.get("citekey", "")).strip(), "no-citekey")
        short_title = _sanitize_file_component(str(metadata.get("short_title", "")).strip() or title, "untitled")
        filename = f"{citekey} - {short_title}.md" if citekey != "no-citekey" else f"{short_title}.md"
        base_dir = "Research/Materials/Literature Notes"
        if category_dir:
            base_dir = f"{base_dir}/{category_dir}"
        return f"{base_dir}/{filename}"

    if note_type == "review":
        base_dir = "Research/Materials/Review Notes"
        if category_dir:
            base_dir = f"{base_dir}/{category_dir}"
        return f"{base_dir}/{_review_file_stem(title, metadata, project_name, filename_style)}.md"

    project_slug = _slugify(project_name or metadata.get("project", "") or title, fallback="materials-project")
    filename = f"{_sanitize_file_component(title or 'project overview', 'project overview')}.md"
    base_dir = "Research/Materials/Projects"
    if category_dir:
        base_dir = f"{base_dir}/{category_dir}"
    return f"{base_dir}/{project_slug}/{filename}"


def _build_note_path(
    note_type: str,
    title: str,
    metadata: dict[str, Any],
    project_name: str,
    note_dirs: dict[str, Path],
    filename_style: str,
    category: str,
) -> Path:
    category_dir = _category_dir_name(category, metadata)
    if note_type == "literature":
        citekey = _sanitize_file_component(str(metadata.get("citekey", "")).strip(), "no-citekey")
        short_title = _sanitize_file_component(str(metadata.get("short_title", "")).strip() or title, "untitled")
        filename = f"{citekey} - {short_title}.md" if citekey != "no-citekey" else f"{short_title}.md"
        literature_dir = note_dirs["literature"] / category_dir if category_dir else note_dirs["literature"]
        return literature_dir / filename

    if note_type == "review":
        review_dir = note_dirs["review"] / category_dir if category_dir else note_dirs["review"]
        return review_dir / f"{_review_file_stem(title, metadata, project_name, filename_style)}.md"

    project_slug = _slugify(project_name or metadata.get("project", "") or title, fallback="materials-project")
    project_base_dir = note_dirs["project"] / category_dir if category_dir else note_dirs["project"]
    project_dir = project_base_dir / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_sanitize_file_component(title or 'project overview', 'project overview')}.md"
    return project_dir / filename


def _timestamped_path(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem}（{timestamp}）{path.suffix}")


def _timestamped_relative_path(relative_path: str) -> str:
    path = Path(relative_path)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem}（{timestamp}）{path.suffix}").as_posix()


def _bridge_bootstrap_materials(vault_dir: str, overwrite_templates: bool, category: str = "") -> dict[str, Any]:
    templates = {
        "Literature Note Template.md": _template_content("literature"),
        "Review Note Template.md": _template_content("review"),
        "Project Note Template.md": _template_content("project"),
    }
    return _bridge_request(
        "POST",
        "/obsidian/bootstrap-materials",
        {
            "vault_dir": vault_dir,
            "category": category,
            "overwrite_templates": overwrite_templates,
            "templates": templates,
        },
        timeout=20.0,
    )


def _bridge_write_text(vault_dir: str, relative_path: str, content: str, overwrite: bool) -> dict[str, Any]:
    return _bridge_request(
        "POST",
        "/obsidian/write-file",
        {
            "vault_dir": vault_dir,
            "relative_path": relative_path,
            "content": content,
            "overwrite": overwrite,
        },
        timeout=20.0,
    )


def _template_content(template_name: str) -> str:
    if template_name == "literature":
        return """---
title: "{{title}}"
authors: []
year:
doi: ""
citekey: ""
zotero_key: ""
category: ""
tags: []
url: ""
zotero_select: ""
pdf_local_path: ""
pdf_local_uri: ""
---

# {{title}}

## Basic Information

## Links

## Abstract
"""

    if template_name == "review":
        return """---
title: "{{title}}"
topic: "{{topic}}"
keywords: []
review_style: "legacy_materials"
tags: ["materials-review"]
---

# {{title}}

## Import Background

## Topic Overview

## Literature Index

## Review Outline
"""

    return """---
title: "{{title}}"
project: "{{project}}"
tags: ["materials-project"]
---

# {{title}}

## Research Goal

## Candidate Alloy and Process Hypotheses

## Data Sources

## Figure Index

## Current Conclusions

## Open Questions

## Next Experiments
"""


def _ensure_materials_layout(runtime_paths: dict[str, Any], overwrite_templates: bool) -> dict[str, list[str]]:
    vault_dir = runtime_paths["vault_dir"]
    materials_root = runtime_paths["materials_root"]
    note_dirs = runtime_paths["note_dirs"]
    templates_dir = runtime_paths["templates_dir"]
    category_dirs = runtime_paths.get("category_dirs", {}) or {}
    created_dirs: list[str] = []
    created_templates: list[str] = []

    required_dirs = [
        materials_root,
        note_dirs["literature"],
        note_dirs["review"],
        templates_dir,
    ]
    for key in ("literature", "review"):
        category_dir = category_dirs.get(key)
        if category_dir is not None:
            required_dirs.append(category_dir)

    for directory in required_dirs:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs.append(_to_rel_path(directory, vault_dir))

    template_paths = {
        "literature": templates_dir / "literature-note.md",
        "review": templates_dir / "review-note.md",
    }
    for template_name, template_path in template_paths.items():
        if overwrite_templates or not template_path.exists():
            template_path.write_text(_template_content(template_name), encoding="utf-8")
            created_templates.append(_to_rel_path(template_path, vault_dir))

    return {"created_dirs": created_dirs, "created_templates": created_templates}


def _frontmatter(
    note_type: str,
    title: str,
    metadata: dict[str, Any],
    relative_note_path: str,
    review_style: str,
    filename_style: str,
) -> str:
    frontmatter: dict[str, Any] = {
        "title": metadata.get("title", title),
        "authors": _normalize_list(metadata.get("authors")),
        "year": metadata.get("year", ""),
        "doi": metadata.get("doi", ""),
        "citekey": metadata.get("citekey", ""),
        "zotero_key": metadata.get("zotero_key", ""),
        "tags": _normalize_list(metadata.get("tags")),
        "alloy_family": metadata.get("alloy_family", ""),
        "property_focus": metadata.get("property_focus", ""),
        "note_type": note_type,
        "materials_root": "Research/Materials",
        "generated_by": "ScienceClaw",
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "vault_path": relative_note_path,
    }
    resolved_category = _metadata_category(metadata)
    if resolved_category:
        frontmatter["category"] = resolved_category

    if note_type == "literature":
        if metadata.get("short_title"):
            frontmatter["short_title"] = metadata.get("short_title")
        for key in (
            "item_type",
            "venue",
            "url",
            "zotero_select",
            "pdf_local_path",
            "pdf_local_uri",
            "citations",
            "jcr_partition",
            "cas_upgrade_partition",
            "impact_factor",
            "impact_factor_5y",
            "ei",
            "arxiv",
            "tldr",
        ):
            value = metadata.get(key)
            if value not in (None, "", [], {}):
                frontmatter[key] = value

    if note_type == "review":
        frontmatter["topic"] = metadata.get("topic", title)
        frontmatter["keywords"] = _normalize_keywords(metadata.get("keywords"))
        frontmatter["review_style"] = review_style
        frontmatter["filename_style"] = filename_style
        if metadata.get("review_bundle_path"):
            frontmatter["review_bundle_path"] = metadata.get("review_bundle_path")
        if metadata.get("source_export_json"):
            frontmatter["source_export_json"] = metadata.get("source_export_json")
        if metadata.get("writing_pass"):
            frontmatter["writing_pass"] = metadata.get("writing_pass")
        if metadata.get("skill_pipeline"):
            frontmatter["skill_pipeline"] = _normalize_list(metadata.get("skill_pipeline"))
        if metadata.get("review_input_path"):
            frontmatter["review_input_path"] = metadata.get("review_input_path")
        if metadata.get("review_draft_path"):
            frontmatter["review_draft_path"] = metadata.get("review_draft_path")
        if metadata.get("source_writing_input_path"):
            frontmatter["source_writing_input_path"] = metadata.get("source_writing_input_path")
        for count_key in ("included_paper_count", "boundary_paper_count", "noise_paper_count"):
            if count_key in metadata:
                frontmatter[count_key] = metadata.get(count_key)
        if metadata.get("pdf_stats"):
            frontmatter["pdf_stats"] = metadata.get("pdf_stats")

    return yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()


def _render_literature_note(title: str, metadata: dict[str, Any], content: str) -> str:
    tags = ", ".join(_normalize_list(metadata.get("tags")))
    basic_info = _render_kv_lines(
        [
            ("Authors", ", ".join(_normalize_list(metadata.get("authors"))) or "Unknown"),
            ("Year", metadata.get("year", "") or "Unknown"),
            ("DOI", metadata.get("doi", "") or "Unknown"),
            ("Citekey", metadata.get("citekey", "") or "Not available"),
            ("Zotero Key", metadata.get("zotero_key", "") or "Not available"),
            ("Category", metadata.get("category", "") or "Not available"),
            ("Item Type", metadata.get("item_type", "") or "Unknown"),
            ("Venue", metadata.get("venue", "") or "Unknown"),
            ("Tags", tags or "Not available"),
        ]
    )

    url = str(metadata.get("url", "")).strip()
    zotero_select = str(metadata.get("zotero_select", "")).strip()
    pdf_local_path = str(metadata.get("pdf_local_path", "")).strip()
    pdf_local_uri = str(metadata.get("pdf_local_uri", "")).strip()
    links = "\n".join(
        line
        for line in [
            f"- URL: [Open source]({url})" if url else "- URL: Not available",
            f"- Zotero Select: [Open in Zotero]({zotero_select})" if zotero_select else "- Zotero Select: Not available",
            f"- PDF Local Path: `{pdf_local_path}`" if pdf_local_path else "- PDF Local Path: Not available",
            f"- PDF Local Link: [Open local PDF]({pdf_local_uri})" if pdf_local_uri else "",
        ]
        if line
    )

    structured_extra = _render_kv_lines(
        [
            ("TLDR", metadata.get("tldr", "")),
            ("Citations", metadata.get("citations", "")),
            ("JCR分区", metadata.get("jcr_partition", "")),
            ("中科院分区升级版", metadata.get("cas_upgrade_partition", "")),
            ("影响因子", metadata.get("impact_factor", "")),
            ("5年影响因子", metadata.get("impact_factor_5y", "")),
            ("EI", metadata.get("ei", "")),
            ("arXiv", metadata.get("arxiv", "")),
        ]
    )

    insights_parts: list[str] = []
    main_insights = _clean_text(metadata.get("insights", ""))
    if main_insights:
        insights_parts.append(main_insights)
    for heading, key in (
        ("工具", "insight_tools"),
        ("方法", "insight_methods"),
        ("其他", "insight_other"),
    ):
        value = _clean_text(metadata.get(key, ""))
        if value:
            insights_parts.append(f"### {heading}\n{value}")
    insights_body = "\n\n".join(part for part in insights_parts if part).strip()

    imported_notes_other = _section_text(
        metadata.get("imported_notes_other"),
        content,
        fallback="",
    )

    blocks = [f"# {title}", ""]
    _append_section(blocks, "Basic Information", basic_info)
    _append_section(blocks, "Links", links)
    _append_section(blocks, "Abstract", metadata.get("abstract", ""))
    _append_section(blocks, "摘要翻译", metadata.get("abstract_translation", ""))
    _append_section(blocks, "摘要总结", metadata.get("abstract_summary", ""))
    _append_section(blocks, "创新点", metadata.get("innovations", ""))
    _append_section(blocks, "结论", metadata.get("conclusion", ""))
    _append_section(blocks, "研究背景", metadata.get("background", ""))
    _append_section(blocks, "研究内容", metadata.get("research_content", ""))
    _append_section(blocks, "计算方法", metadata.get("methods", ""))
    _append_section(blocks, "结果分析", metadata.get("results_analysis", ""))
    _append_section(blocks, "启示", insights_body)
    _append_section(blocks, "Structured Metadata", structured_extra)
    _append_section(blocks, "Imported Notes / Other", imported_notes_other)
    _append_section(blocks, "Imported Metadata / Other", metadata.get("extra_raw", ""))
    return "\n".join(blocks).strip() + "\n"


def _render_review_note_legacy(title: str, metadata: dict[str, Any], content: str) -> str:
    background = content.strip() or str(metadata.get("background", "")).strip() or "Pending import background."
    overview = (
        str(metadata.get("topic_overview", "")).strip()
        or str(metadata.get("summary", "")).strip()
        or "Pending topic overview."
    )
    outline = _render_bullets(
        _normalize_list(metadata.get("next_review_steps")),
        "Promote imported paper notes into a comparative synthesis draft.",
    )
    return f"""# {title}

## Import Background
{background}

## Topic Overview
{overview}

## Literature Index
{_render_reference_block(metadata.get("references", []), "No literature index yet.")}

## Review Outline
{outline}
"""


def _bridge_bootstrap_materials(vault_dir: str, overwrite_templates: bool, category: str = "") -> dict[str, Any]:
    templates = {
        "literature-note.md": _template_content("literature"),
        "review-note.md": _template_content("review"),
    }
    return _bridge_request(
        "POST",
        "/obsidian/bootstrap-materials",
        {
            "vault_dir": vault_dir,
            "category": category,
            "overwrite_templates": overwrite_templates,
            "templates": templates,
        },
        timeout=20.0,
    )


def _bridge_prune_materials_legacy(vault_dir: str) -> dict[str, Any]:
    return _bridge_request(
        "POST",
        "/obsidian/prune-materials-legacy",
        {
            "vault_dir": vault_dir,
        },
        timeout=20.0,
    )


def _render_body(note_type: str, title: str, metadata: dict[str, Any], content: str, review_style: str) -> str:
    if note_type == "literature":
        return _render_literature_note(title, metadata, content)
    if note_type == "review":
        if review_style == "survey_cn":
            return _render_review_note_survey_cn(title, metadata, content)
        return _render_review_note_legacy(title, metadata, content)
    return _render_project_note(title, metadata, content)


@tool
def obsidian_write_materials_note(
    note_type: str,
    title: str = "",
    content: str = "",
    metadata_json: str = "{}",
    project_name: str = "",
    category: str = "",
    vault_dir: str = "",
    overwrite: bool = False,
    bootstrap_only: bool = False,
    review_style: str = "survey_cn",
    filename_style: str = "title",
    conflict_mode: str = "timestamp",
) -> dict:
    """Create or update AI-for-materials notes inside the mounted Obsidian vault."""
    logger.info(
        "[obsidian_write_materials_note] note_type=%s title=%r project_name=%r vault_dir=%r overwrite=%s bootstrap_only=%s review_style=%s filename_style=%s conflict_mode=%s",
        note_type,
        title,
        project_name,
        vault_dir,
        overwrite,
        bootstrap_only,
        review_style,
        filename_style,
        conflict_mode,
    )

    normalized_note_type = note_type.strip().lower()
    if normalized_note_type not in _VALID_NOTE_TYPES:
        return {
            "ok": False,
            "error": f"Unsupported note_type '{note_type}'. Expected one of: {sorted(_VALID_NOTE_TYPES)}",
        }

    normalized_review_style = review_style.strip().lower()
    if normalized_review_style not in _VALID_REVIEW_STYLES:
        return {
            "ok": False,
            "error": f"Unsupported review_style '{review_style}'. Expected one of: {sorted(_VALID_REVIEW_STYLES)}",
        }

    normalized_filename_style = filename_style.strip().lower()
    if normalized_filename_style not in _VALID_FILENAME_STYLES:
        return {
            "ok": False,
            "error": f"Unsupported filename_style '{filename_style}'. Expected one of: {sorted(_VALID_FILENAME_STYLES)}",
        }

    normalized_conflict_mode = conflict_mode.strip().lower()
    if normalized_conflict_mode not in _VALID_CONFLICT_MODES:
        return {
            "ok": False,
            "error": f"Unsupported conflict_mode '{conflict_mode}'. Expected one of: {sorted(_VALID_CONFLICT_MODES)}",
        }

    try:
        metadata = json.loads(metadata_json) if metadata_json.strip() else {}
    except json.JSONDecodeError as exc:
        logger.error("[obsidian_write_materials_note] invalid metadata_json: %s", exc)
        return {"ok": False, "error": f"Invalid metadata_json: {exc}"}

    if not isinstance(metadata, dict):
        return {"ok": False, "error": "metadata_json must decode to a JSON object"}

    resolved_category = _resolve_category_value(category, metadata)
    if resolved_category and not _metadata_category(metadata):
        metadata = dict(metadata)
        metadata["category"] = resolved_category

    skill_usage = _skill_usage_report(metadata)

    if normalized_note_type != "review":
        normalized_review_style = "legacy_materials"
        normalized_filename_style = "title-review"
        if normalized_note_type == "literature" and normalized_conflict_mode == "timestamp" and not overwrite:
            normalized_conflict_mode = "error"

    if _should_use_host_bridge(vault_dir):
        bridge_bootstrap = _bridge_bootstrap_materials(vault_dir, overwrite_templates=False, category=resolved_category)
        if not bridge_bootstrap.get("ok"):
            failure_report = _vault_report(
                vault_dir,
                str(((bridge_bootstrap.get("data", {}) or {}).get("vault_dir", ""))),
                "host_bridge",
            )
            return {
                "ok": False,
                "error": (bridge_bootstrap.get("data", {}) or {}).get("error", "Host bridge bootstrap failed"),
                "vault_dir": vault_dir,
                "vault_source": "host_bridge",
                "bridge_url": bridge_bootstrap.get("bridge_url", ""),
                **skill_usage,
                **failure_report,
            }

        bridge_layout = bridge_bootstrap.get("data", {}) or {}
        bridge_created_dirs = _sanitize_created_dirs(bridge_layout.get("created_dirs", []))
        bridge_created_templates = _sanitize_created_templates(bridge_layout.get("created_templates", []))
        effective_vault_dir = str(bridge_layout.get("vault_dir", vault_dir))
        vault_report = _vault_report(vault_dir, effective_vault_dir, "host_bridge")
        if vault_report["vault_match_status"] == "fallback_other_path":
            return {
                "ok": False,
                "error": (
                    "Host bridge bootstrap resolved a different vault than requested. "
                    f"requested={vault_report['requested_vault_dir']!r}, "
                    f"effective={vault_report['effective_vault_dir']!r}"
                ),
                "vault_dir": effective_vault_dir,
                "vault_source": "host_bridge",
                "bridge_url": bridge_bootstrap.get("bridge_url", ""),
                "materials_root": str(bridge_layout.get("materials_root", "")),
                "category": resolved_category,
                "created_dirs": bridge_created_dirs,
                "created_templates": bridge_created_templates,
                **skill_usage,
                **vault_report,
            }

        prune_result = _bridge_prune_materials_legacy(vault_dir)
        pruned_legacy_dirs = []
        if prune_result.get("ok"):
            pruned_legacy_dirs = _sanitize_created_dirs((prune_result.get("data", {}) or {}).get("removed_dirs", []))

        if bootstrap_only:
            return {
                "ok": True,
                "bootstrap_only": True,
                "vault_dir": effective_vault_dir,
                "vault_source": "host_bridge",
                "bridge_url": bridge_bootstrap.get("bridge_url", ""),
                "materials_root": str(bridge_layout.get("materials_root", "")),
                "category": resolved_category,
                "created_dirs": bridge_created_dirs,
                "created_templates": bridge_created_templates,
                "pruned_legacy_dirs": pruned_legacy_dirs,
                **skill_usage,
                **vault_report,
            }

        resolved_title = str(title).strip() or str(metadata.get("title", "")).strip()
        if not resolved_title:
            return {"ok": False, "error": "title is required unless metadata_json contains a non-empty title"}

        relative_note_path = _build_note_relative_path(
            normalized_note_type,
            resolved_title,
            metadata,
            project_name,
            normalized_filename_style,
            resolved_category,
        )
        frontmatter = _frontmatter(
            normalized_note_type,
            resolved_title,
            metadata,
            relative_note_path,
            normalized_review_style,
            normalized_filename_style,
        )
        body = _render_body(normalized_note_type, resolved_title, metadata, content, normalized_review_style)
        note_text = f"---\n{frontmatter}\n---\n\n{body}".strip() + "\n"

        bridge_write = _bridge_write_text(vault_dir, relative_note_path, note_text, overwrite)
        if (
            not bridge_write.get("ok")
            and not overwrite
            and normalized_conflict_mode == "timestamp"
            and bridge_write.get("status_code") == 409
        ):
            relative_note_path = _timestamped_relative_path(relative_note_path)
            frontmatter = _frontmatter(
                normalized_note_type,
                resolved_title,
                metadata,
                relative_note_path,
                normalized_review_style,
                normalized_filename_style,
            )
            note_text = f"---\n{frontmatter}\n---\n\n{body}".strip() + "\n"
            bridge_write = _bridge_write_text(vault_dir, relative_note_path, note_text, overwrite=False)

        if not bridge_write.get("ok"):
            failure_report = _vault_report(
                vault_dir,
                str(((bridge_write.get("data", {}) or {}).get("vault_dir", effective_vault_dir))),
                "host_bridge",
            )
            return {
                "ok": False,
                "error": (bridge_write.get("data", {}) or {}).get("error", "Host bridge write failed"),
                "vault_dir": vault_dir,
                "vault_source": "host_bridge",
                "bridge_url": bridge_write.get("bridge_url", ""),
                "created_dirs": bridge_created_dirs,
                "created_templates": bridge_created_templates,
                **skill_usage,
                **failure_report,
            }

        prune_result = _bridge_prune_materials_legacy(vault_dir)
        pruned_legacy_dirs = []
        if prune_result.get("ok"):
            pruned_legacy_dirs = _sanitize_created_dirs((prune_result.get("data", {}) or {}).get("removed_dirs", []))

        write_data = bridge_write.get("data", {}) or {}
        write_vault_dir = str(write_data.get("vault_dir", effective_vault_dir))
        write_vault_report = _vault_report(vault_dir, write_vault_dir, "host_bridge")
        if write_vault_report["vault_match_status"] == "fallback_other_path":
            return {
                "ok": False,
                "error": (
                    "Host bridge write resolved a different vault than requested. "
                    f"requested={write_vault_report['requested_vault_dir']!r}, "
                    f"effective={write_vault_report['effective_vault_dir']!r}"
                ),
                "vault_dir": write_vault_dir,
                "vault_source": "host_bridge",
                "bridge_url": bridge_write.get("bridge_url", ""),
                "created_dirs": bridge_created_dirs,
                "created_templates": bridge_created_templates,
                **skill_usage,
                **write_vault_report,
            }

        absolute_path = str(write_data.get("absolute_path", ""))
        result = {
            "ok": True,
            "vault_dir": write_vault_dir,
            "vault_source": "host_bridge",
            "bridge_url": bridge_write.get("bridge_url", ""),
            "materials_root": str(bridge_layout.get("materials_root", "")),
            "category": resolved_category,
            "note_path": absolute_path,
            "relative_note_path": relative_note_path,
            "project_dir": str(Path(absolute_path).parent) if normalized_note_type == "project" and absolute_path else "",
            "created_dirs": bridge_created_dirs,
            "created_templates": bridge_created_templates,
            "pruned_legacy_dirs": pruned_legacy_dirs,
            "review_style": normalized_review_style,
            "filename_style": normalized_filename_style,
            "conflict_mode": normalized_conflict_mode,
            **skill_usage,
            **write_vault_report,
        }
        return result

    runtime_paths = _resolve_runtime_paths(vault_dir, resolved_category)
    resolved_vault_dir = runtime_paths["vault_dir"]
    materials_root = runtime_paths["materials_root"]
    note_dirs = runtime_paths["note_dirs"]
    vault_report = _vault_report(vault_dir, str(resolved_vault_dir), runtime_paths["vault_source"])

    layout_result = _ensure_materials_layout(runtime_paths, overwrite_templates=False)
    sanitized_layout_result = {
        "created_dirs": _sanitize_created_dirs(layout_result.get("created_dirs", [])),
        "created_templates": _sanitize_created_templates(layout_result.get("created_templates", [])),
    }
    if bootstrap_only:
        result = {
            "ok": True,
            "bootstrap_only": True,
            "vault_dir": str(resolved_vault_dir),
            "vault_source": runtime_paths["vault_source"],
            "materials_root": str(materials_root),
            "category": resolved_category,
            **sanitized_layout_result,
            **skill_usage,
            **vault_report,
        }
        return result

    resolved_title = str(title).strip() or str(metadata.get("title", "")).strip()
    if not resolved_title:
        return {"ok": False, "error": "title is required unless metadata_json contains a non-empty title"}

    note_path = _build_note_path(
        normalized_note_type,
        resolved_title,
        metadata,
        project_name,
        note_dirs,
        normalized_filename_style,
        resolved_category,
    )
    if note_path.exists() and not overwrite:
        if normalized_conflict_mode == "timestamp":
            note_path = _timestamped_path(note_path)
        else:
            relative_note_path = _to_rel_path(note_path, resolved_vault_dir)
            result = {
                "ok": False,
                "error": f"Note already exists: {relative_note_path}. Set overwrite=true to replace it.",
                **sanitized_layout_result,
                **skill_usage,
                **vault_report,
            }
            return result

    relative_note_path = _to_rel_path(note_path, resolved_vault_dir)
    frontmatter = _frontmatter(
        normalized_note_type,
        resolved_title,
        metadata,
        relative_note_path,
        normalized_review_style,
        normalized_filename_style,
    )
    body = _render_body(normalized_note_type, resolved_title, metadata, content, normalized_review_style)
    note_text = f"---\n{frontmatter}\n---\n\n{body}".strip() + "\n"

    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(note_text, encoding="utf-8")

    logger.info("[obsidian_write_materials_note] wrote note=%s", relative_note_path)
    result = {
        "ok": True,
        "vault_dir": str(resolved_vault_dir),
        "vault_source": runtime_paths["vault_source"],
        "materials_root": str(materials_root),
        "category": resolved_category,
        "note_path": str(note_path),
        "relative_note_path": relative_note_path,
        "project_dir": str(note_path.parent) if normalized_note_type == "project" else "",
        "created_dirs": sanitized_layout_result.get("created_dirs", []),
        "created_templates": sanitized_layout_result.get("created_templates", []),
        "review_style": normalized_review_style,
        "filename_style": normalized_filename_style,
        "conflict_mode": normalized_conflict_mode,
        **skill_usage,
        **vault_report,
    }
    return result
