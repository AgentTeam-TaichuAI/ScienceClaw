import importlib.util
import json
import logging
import re
from collections import Counter
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Obsidian",
    "subcategory": "Import",
    "tags": ["obsidian", "zotero", "better-bibtex", "materials"],
}

_SKIP_ITEM_TYPES = {"attachment", "note"}
_WRITER_TOOL = None
_EXTRA_FIELD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^TLDR\s*[:：]\s*(.+)$", re.IGNORECASE), "tldr"),
    (re.compile(r"^(\d+\s+citations?(?:\s*\([^)]*\))?(?:\s*\[[^\]]+\])?)$", re.IGNORECASE), "citations"),
    (re.compile(r"^citations?(?:\s*\([^)]*\))?\s*[:：]\s*(.+)$", re.IGNORECASE), "citations"),
    (re.compile(r"^JCR分区\s*[:：]\s*(.+)$", re.IGNORECASE), "jcr_partition"),
    (re.compile(r"^中科院分区升级版\s*[:：]\s*(.+)$", re.IGNORECASE), "cas_upgrade_partition"),
    (re.compile(r"^(?:5年影响因子|五年影响因子)\s*[:：]\s*(.+)$", re.IGNORECASE), "impact_factor_5y"),
    (re.compile(r"^影响因子\s*[:：]\s*(.+)$", re.IGNORECASE), "impact_factor"),
    (re.compile(r"^EI\s*[:：]\s*(.+)$", re.IGNORECASE), "ei"),
    (re.compile(r"^arXiv\s*[:：]\s*(.+)$", re.IGNORECASE), "arxiv"),
]
_TEXT_SECTION_LABELS: dict[str, str] = {
    "abstract_translation": "摘要翻译",
    "abstract_summary": "摘要总结",
    "innovations": "创新点",
    "conclusion": "结论",
    "background": "研究背景",
    "research_content": "研究内容",
    "methods": "计算方法",
    "results_analysis": "结果分析",
    "insights": "启示",
    "insight_tools": "工具",
    "insight_methods": "方法",
    "insight_other": "其他",
}


class _ZoteroNoteHTMLParser(HTMLParser):
    _HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    _TEXT_TAGS = {"p", "li", "td", "th"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, Any]] = []
        self._current_tag = ""
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in self._HEADING_TAGS or lowered in self._TEXT_TAGS:
            self._flush()
            self._current_tag = lowered
            return
        if lowered == "br":
            self._buffer.append("\n")
            return
        if lowered in {"hr", "tr"}:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == self._current_tag:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._current_tag:
            self._buffer.append(data)

    def _flush(self) -> None:
        text = _clean_text(unescape("".join(self._buffer)))
        if text:
            if self._current_tag in self._HEADING_TAGS:
                self.blocks.append(
                    {
                        "kind": "heading",
                        "level": int(self._current_tag[1]),
                        "text": text,
                    }
                )
            elif self._current_tag in self._TEXT_TAGS:
                self.blocks.append({"kind": "text", "text": text})
        self._current_tag = ""
        self._buffer = []


def _load_writer_tool():
    global _WRITER_TOOL
    if _WRITER_TOOL is not None:
        return _WRITER_TOOL

    tool_path = Path(__file__).with_name("obsidian_write_materials_note.py")
    spec = importlib.util.spec_from_file_location("obsidian_write_materials_note_module", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load writer tool from {tool_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    writer = getattr(module, "obsidian_write_materials_note", None)
    if writer is None or not hasattr(writer, "invoke"):
        raise RuntimeError("obsidian_write_materials_note tool is unavailable")

    _WRITER_TOOL = writer
    return writer


def _normalize_tags(raw_tags: Any) -> list[str]:
    if not raw_tags:
        return []

    tags: list[str] = []
    for entry in raw_tags:
        if isinstance(entry, str):
            tag = entry.strip()
        elif isinstance(entry, dict):
            tag = str(entry.get("tag", "")).strip()
        else:
            tag = str(entry).strip()
        if tag:
            tags.append(tag)
    return tags


def _creator_names(creators: Any) -> list[str]:
    if not creators:
        return []

    names: list[str] = []
    for creator in creators:
        if not isinstance(creator, dict):
            continue
        if creator.get("creatorType") not in (None, "", "author"):
            continue
        first_name = str(creator.get("firstName", "")).strip()
        last_name = str(creator.get("lastName", "")).strip()
        full_name = " ".join(part for part in [first_name, last_name] if part)
        if not full_name:
            full_name = str(creator.get("name", "")).strip()
        if full_name:
            names.append(full_name)
    return names


def _extract_year(item: dict[str, Any]) -> str:
    for key in ("date", "year", "issued"):
        value = str(item.get(key, "")).strip()
        if not value:
            continue
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            return match.group(0)
    return ""


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned, maxsplit=1)
    sentence = parts[0].strip()
    if len(sentence) > 320:
        return sentence[:317].rstrip() + "..."
    return sentence


def _topic_slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", cleaned).strip("-_").lower() or "materials-topic"


def _normalize_category(value: str, topic: str) -> str:
    explicit = str(value or "").strip()
    topic_text = str(topic or "").strip()
    if not explicit:
        return topic_text
    explicit_slug = _topic_slug(explicit)
    topic_slug = _topic_slug(topic_text) if topic_text else ""
    if explicit_slug in {"material", "materials"} and topic_slug and explicit_slug != topic_slug:
        return topic_text
    return explicit


def _safe_folder_component(value: str, fallback: str = "") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n]+', " ", str(value or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned[:120].strip()
    return cleaned or fallback


def _append_unique(chunks: list[str], value: Any) -> None:
    text = _clean_text(value)
    if text and text not in chunks:
        chunks.append(text)


def _collapse_chunks(chunks: list[str]) -> str:
    return "\n\n".join(chunk for chunk in chunks if chunk).strip()


def _normalize_heading_key(value: str) -> str:
    text = _clean_text(value)
    text = text.replace("&amp;", " ").replace("&nbsp;", " ").replace("&", " ")
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text, flags=re.UNICODE)
    return text.lower()


def _canonical_note_section(heading_text: str, level: int) -> str:
    normalized = _normalize_heading_key(heading_text)
    if not normalized:
        return ""
    if level == 1:
        return "__ignore__"
    if "metadata" in normalized or normalized == "metadata":
        return "__ignore__"
    if normalized in {"摘要", "abstract"} or ("摘要" in normalized and "翻译" not in normalized and "总结" not in normalized):
        return "abstract"
    if "摘要翻译" in normalized:
        return "abstract_translation"
    if "摘要总结" in normalized:
        return "abstract_summary"
    if "创新点" in normalized:
        return "innovations"
    if "结论" in normalized:
        return "conclusion"
    if "研究背景" in normalized or ("背景" in normalized and "目的" in normalized) or "研究背景基础目的" in normalized:
        return "background"
    if "研究内容" in normalized:
        return "research_content"
    if "计算方法" in normalized:
        return "methods"
    if "结果分析" in normalized:
        return "results_analysis"
    if normalized.startswith("启示"):
        return "insights"
    if normalized == "工具":
        return "insight_tools"
    if normalized == "方法":
        return "insight_methods"
    if normalized == "其他":
        return "insight_other"
    return ""


def _parse_note_sections(note_html: str) -> dict[str, str]:
    parser = _ZoteroNoteHTMLParser()
    try:
        parser.feed(str(note_html or ""))
        parser.close()
    except Exception:
        plain = _clean_text(re.sub(r"(?is)<[^>]+>", " ", str(note_html or "")))
        return {"imported_notes_other": plain} if plain else {}

    collected: dict[str, list[str]] = {}
    current_section = ""
    current_heading = ""
    for block in parser.blocks:
        if block.get("kind") == "heading":
            current_heading = str(block.get("text", "")).strip()
            current_section = _canonical_note_section(current_heading, int(block.get("level", 2)))
            continue

        text = _clean_text(block.get("text", ""))
        if not text:
            continue
        if current_section == "__ignore__":
            continue
        if current_section:
            collected.setdefault(current_section, [])
            _append_unique(collected[current_section], text)
            continue
        if current_heading:
            labeled = f"### {current_heading}\n{text}"
            collected.setdefault("imported_notes_other", [])
            _append_unique(collected["imported_notes_other"], labeled)
            continue
        collected.setdefault("imported_notes_other", [])
        _append_unique(collected["imported_notes_other"], text)

    return {key: _collapse_chunks(values) for key, values in collected.items() if values}


def _collect_note_sections(notes: Any) -> dict[str, str]:
    collected: dict[str, list[str]] = {}
    for entry in notes or []:
        if isinstance(entry, dict):
            note_text = str(entry.get("note", "") or entry.get("title", ""))
        else:
            note_text = str(entry or "")
        parsed = _parse_note_sections(note_text)
        if not parsed:
            plain = _clean_text(re.sub(r"(?is)<[^>]+>", " ", note_text))
            if plain:
                parsed = {"imported_notes_other": plain}
        for key, value in parsed.items():
            collected.setdefault(key, [])
            _append_unique(collected[key], value)
    return {key: _collapse_chunks(values) for key, values in collected.items() if values}


def _merge_field(existing: str, new_value: str) -> str:
    if not existing:
        return new_value
    if new_value in existing:
        return existing
    return f"{existing}; {new_value}"


def _parse_extra_metadata(extra: Any) -> tuple[dict[str, str], str]:
    structured: dict[str, str] = {}
    raw_lines: list[str] = []
    current_key = ""
    current_target = ""
    for raw_line in _clean_text(extra).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for pattern, key in _EXTRA_FIELD_PATTERNS:
            match = pattern.match(line)
            if match:
                structured[key] = _merge_field(structured.get(key, ""), match.group(1).strip())
                current_key = key
                current_target = "structured"
                matched = True
                break
        if matched:
            continue
        if ":" not in line and current_target == "structured" and current_key:
            structured[current_key] = _merge_field(structured.get(current_key, ""), line)
            continue
        if ":" not in line and raw_lines:
            raw_lines[-1] = f"{raw_lines[-1]} {line}".strip()
            current_target = "raw"
            current_key = ""
            continue
        raw_lines.append(line)
        current_target = "raw"
        current_key = ""
    return structured, "\n".join(raw_lines).strip()


def _path_to_file_uri(path_value: str) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""
    if raw.startswith(("file://", "http://", "https://")):
        return raw
    if re.match(r"^[A-Za-z]:[\\/]", raw):
        normalized = raw.replace("\\", "/")
        return "file:///" + quote(normalized, safe="/:")
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        try:
            return candidate.resolve().as_uri()
        except Exception:
            return "file://" + quote(str(candidate).replace("\\", "/"), safe="/:")
    return ""


def _extract_attachment_metadata(attachments: Any, item_select: str = "") -> dict[str, Any]:
    pdf_local_path = ""
    pdf_local_uri = ""
    pdf_select = ""
    lines: list[str] = []
    for entry in attachments or []:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip() or "Attachment"
        path = str(entry.get("path", "")).strip()
        url = str(entry.get("url", "")).strip()
        select = str(entry.get("select", "")).strip()
        suffix = Path(path or url).suffix.lower()
        if suffix == ".pdf" and path and not pdf_local_path:
            pdf_local_path = path
            pdf_local_uri = _path_to_file_uri(path)
            pdf_select = select
        details = [title]
        if path:
            details.append(f"path={path}")
        elif url:
            details.append(f"url={url}")
        if select:
            details.append(f"zotero={select}")
        lines.append("- " + "; ".join(details))
    return {
        "pdf_local_path": pdf_local_path,
        "pdf_local_uri": pdf_local_uri,
        "pdf_select": pdf_select,
        "attachment_inventory": "\n".join(lines).strip(),
        "zotero_select": item_select or pdf_select,
    }


def _topic_overview(topic: str, category: str, imported_count: int, type_counter: Counter[str], year_counter: Counter[str]) -> str:
    type_bits = ", ".join(f"{name}: {count}" for name, count in sorted(type_counter.items()))
    year_bits = ", ".join(f"{year}: {count}" for year, count in sorted(year_counter.items(), reverse=True) if year)
    return "\n".join(
        [
            f"- Topic: {topic}",
            f"- Category: {category}",
            f"- Imported references: {imported_count}",
            f"- Item types: {type_bits or 'Unknown'}",
            f"- Year distribution: {year_bits or 'Unknown'}",
        ]
    )


def _attachment_block(attachments: Any) -> str:
    if not attachments:
        return "- No attachment metadata exported."

    lines: list[str] = []
    for entry in attachments:
        if not isinstance(entry, dict):
            lines.append(f"- {entry}")
            continue
        title = str(entry.get("title", "")).strip() or "Attachment"
        path = str(entry.get("path", "")).strip()
        url = str(entry.get("url", "")).strip()
        select = str(entry.get("select", "")).strip()
        details = [title]
        if path:
            details.append(f"path={path}")
        elif url:
            details.append(f"url={url}")
        if select:
            details.append(f"zotero={select}")
        lines.append("- " + "; ".join(details))
    return "\n".join(lines)


def _notes_block(notes: Any) -> str:
    if not notes:
        return "- No Zotero notes exported."

    lines: list[str] = []
    for index, entry in enumerate(notes, start=1):
        if isinstance(entry, dict):
            note_text = _clean_text(entry.get("note", "") or entry.get("title", ""))
        else:
            note_text = _clean_text(entry)
        if not note_text:
            continue
        if len(note_text) > 500:
            note_text = note_text[:497].rstrip() + "..."
        lines.append(f"- Note {index}: {note_text}")
    return "\n".join(lines) if lines else "- Zotero notes were exported but empty."


def _relative_review_path(topic: str, category: str = "") -> str:
    base_dir = "Research/Materials/Review Notes"
    category_dir = _safe_folder_component(category)
    if category_dir:
        base_dir = f"{base_dir}/{category_dir}"
    return f"{base_dir}/{_safe_folder_component(topic, 'materials-topic')} - review.md"


def _review_background(topic: str, export_path: str, imported_count: int, type_counter: Counter[str], year_counter: Counter[str]) -> str:
    type_bits = ", ".join(f"{name}: {count}" for name, count in sorted(type_counter.items()))
    year_bits = ", ".join(f"{year}: {count}" for year, count in sorted(year_counter.items(), reverse=True) if year)
    lines = [
        f"This review note was scaffolded from the Zotero Better BibTeX export `{export_path}`.",
        f"",
        f"- Topic: {topic}",
        f"- Imported references: {imported_count}",
        f"- Item types: {type_bits or 'Unknown'}",
        f"- Year distribution: {year_bits or 'Unknown'}",
        f"",
        "Use this note to track topic framing, literature indexing, and the next synthesis pass.",
    ]
    return "\n".join(lines)


def _paper_bullet(item: dict[str, Any], relative_note_path: str) -> str:
    year = _extract_year(item) or "n.d."
    title = str(item.get("title", "")).strip() or "Untitled"
    summary_source = _clean_text(item.get("abstractNote", ""))
    summary = _first_sentence(summary_source) or "Abstract missing in export."
    return f"[[{relative_note_path}]] ({year}) - {title}: {summary}"


def _item_metadata(
    item: dict[str, Any],
    topic: str,
    topic_tag: str,
    category: str,
    alloy_family: str,
    property_focus: str,
    review_path: str,
) -> dict[str, Any]:
    title = str(item.get("title", "")).strip() or "Untitled"
    abstract = _clean_text(item.get("abstractNote", ""))
    tags = _normalize_tags(item.get("tags", []))
    derived_tags = list(dict.fromkeys(tags + ["materials", "zotero-import", topic_tag]))
    year = _extract_year(item)
    venue = str(
        item.get("publicationTitle", "")
        or item.get("proceedingsTitle", "")
        or item.get("publisher", "")
        or item.get("archive", "")
    ).strip()
    item_select = str(item.get("select", "")).strip()
    note_sections = _collect_note_sections(item.get("notes", []))
    extra_fields, extra_raw = _parse_extra_metadata(item.get("extra", ""))
    attachment_metadata = _extract_attachment_metadata(item.get("attachments", []), item_select=item_select)

    abstract_section = abstract or note_sections.get("abstract", "")
    one_sentence_summary = (
        extra_fields.get("tldr", "")
        or _first_sentence(abstract_section)
        or f"Imported from Zotero export for topic {topic}."
    )
    return {
        "title": title,
        "short_title": str(item.get("shortTitle", "")).strip() or title,
        "authors": _creator_names(item.get("creators", [])),
        "year": year,
        "doi": str(item.get("DOI", "")).strip(),
        "citekey": str(item.get("citationKey", "")).strip(),
        "zotero_key": str(item.get("itemKey", "") or item.get("key", "")).strip(),
        "tags": derived_tags,
        "category": category,
        "alloy_family": alloy_family,
        "property_focus": property_focus,
        "item_type": str(item.get("itemType", "")).strip() or "unknown",
        "venue": venue,
        "url": str(item.get("url", "")).strip(),
        "zotero_select": attachment_metadata.get("zotero_select", ""),
        "pdf_local_path": attachment_metadata.get("pdf_local_path", ""),
        "pdf_local_uri": attachment_metadata.get("pdf_local_uri", ""),
        "attachment_inventory": attachment_metadata.get("attachment_inventory", ""),
        "one_sentence_summary": one_sentence_summary,
        "tldr": extra_fields.get("tldr", ""),
        "citations": extra_fields.get("citations", ""),
        "jcr_partition": extra_fields.get("jcr_partition", ""),
        "cas_upgrade_partition": extra_fields.get("cas_upgrade_partition", ""),
        "impact_factor": extra_fields.get("impact_factor", ""),
        "impact_factor_5y": extra_fields.get("impact_factor_5y", ""),
        "ei": extra_fields.get("ei", ""),
        "arxiv": extra_fields.get("arxiv", ""),
        "extra_raw": extra_raw,
        "abstract": abstract_section,
        "abstract_translation": note_sections.get("abstract_translation", ""),
        "abstract_summary": note_sections.get("abstract_summary", ""),
        "innovations": note_sections.get("innovations", ""),
        "conclusion": note_sections.get("conclusion", ""),
        "background": note_sections.get("background", ""),
        "research_content": note_sections.get("research_content", ""),
        "methods": note_sections.get("methods", ""),
        "results_analysis": note_sections.get("results_analysis", ""),
        "insights": note_sections.get("insights", ""),
        "insight_tools": note_sections.get("insight_tools", ""),
        "insight_methods": note_sections.get("insight_methods", ""),
        "insight_other": note_sections.get("insight_other", ""),
        "imported_notes_other": note_sections.get("imported_notes_other", ""),
    }


def _item_content(item: dict[str, Any]) -> str:
    return ""


@tool
def obsidian_import_zotero_bbt_json(
    export_json_path: str,
    topic: str = "",
    category: str = "",
    max_items: int = 0,
    alloy_family: str = "",
    property_focus: str = "",
    vault_dir: str = "",
    overwrite_existing: bool = False,
    create_review_note: bool = True,
) -> dict:
    """Import a Better BibTeX JSON export into the Materials area of an Obsidian vault.

    Use this when you already have a Zotero Better BibTeX JSON snapshot and want
    to batch-create literature notes plus a scaffold review note inside
    `Research/Materials/`. This is the fastest way to test the full Zotero ->
    Obsidian path without relying on a live Zotero bridge.

    Args:
        export_json_path: Absolute or repo-relative path to a Better BibTeX JSON
            export file such as `zotero/生成模型.json`.
        topic: Review topic name. When omitted, the JSON filename stem is used.
        max_items: Maximum number of parent references to import. Use `0` for all.
        alloy_family: Optional alloy family written into note frontmatter.
        property_focus: Optional property or theme written into note frontmatter.
        vault_dir: Preferred Obsidian vault path. In Linux/Docker runtimes,
            Windows host paths fall back to the mounted `/home/scienceclaw/obsidian_vault`.
        overwrite_existing: When true, replace existing literature/review notes.
        create_review_note: When true, also generate `<topic> - review.md`.

    Returns:
        A dict summarizing imported literature notes, skipped items, and the
        optional review note path.
    """
    logger.info(
        "[obsidian_import_zotero_bbt_json] export_json_path=%r topic=%r max_items=%s vault_dir=%r overwrite_existing=%s create_review_note=%s",
        export_json_path,
        topic,
        max_items,
        vault_dir,
        overwrite_existing,
        create_review_note,
    )

    export_path = Path(export_json_path).expanduser()
    if not export_path.is_absolute():
        export_path = Path.cwd() / export_path
    if not export_path.exists():
        return {"ok": False, "error": f"Export JSON not found: {export_path}"}

    try:
        payload = json.loads(export_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("[obsidian_import_zotero_bbt_json] invalid JSON: %s", exc)
        return {"ok": False, "error": f"Invalid JSON: {exc}"}

    items = payload.get("items", [])
    if not isinstance(items, list):
        return {"ok": False, "error": "Expected `items` to be a list in Better BibTeX export"}

    resolved_topic = topic.strip() or export_path.stem
    resolved_category = _normalize_category(category, resolved_topic)
    writer = _load_writer_tool()
    bootstrap_result = writer.invoke(
        {
            "note_type": "literature",
            "category": resolved_category,
            "vault_dir": vault_dir,
            "bootstrap_only": True,
            "conflict_mode": "error",
        }
    )
    if not bootstrap_result.get("ok"):
        return {
            "ok": False,
            "error": bootstrap_result.get("error", "Failed to bootstrap Materials workspace"),
            "bootstrap_result": bootstrap_result,
            "requested_vault_dir": bootstrap_result.get("requested_vault_dir", str(vault_dir or "").strip()),
            "effective_vault_dir": bootstrap_result.get("effective_vault_dir", ""),
            "effective_vault_source": bootstrap_result.get("effective_vault_source", ""),
            "fell_back_to_default_vault": bootstrap_result.get("fell_back_to_default_vault", False),
        }

    topic_tag = _topic_slug(resolved_topic)

    imported_notes: list[dict[str, Any]] = []
    skipped_items: list[dict[str, Any]] = []
    type_counter: Counter[str] = Counter()
    year_counter: Counter[str] = Counter()

    parent_items = [item for item in items if isinstance(item, dict) and item.get("itemType") not in _SKIP_ITEM_TYPES]
    limit = len(parent_items) if max_items <= 0 else min(max_items, len(parent_items))

    for item in parent_items[:limit]:
        item_type = str(item.get("itemType", "")).strip() or "unknown"
        type_counter[item_type] += 1
        year_counter[_extract_year(item)] += 1

        metadata = _item_metadata(
            item=item,
            topic=resolved_topic,
            topic_tag=topic_tag,
            category=resolved_category,
            alloy_family=alloy_family,
            property_focus=property_focus,
            review_path="",
        )
        result = writer.invoke(
            {
                "note_type": "literature",
                "title": metadata["title"],
                "content": _item_content(item),
                "metadata_json": json.dumps(metadata, ensure_ascii=False),
                "project_name": resolved_topic,
                "category": resolved_category,
                "vault_dir": vault_dir,
                "overwrite": overwrite_existing,
                "conflict_mode": "error",
            }
        )
        if not result.get("ok"):
            skipped_items.append(
                {
                    "title": metadata["title"],
                    "itemType": item_type,
                    "reason": result.get("error", "Unknown write failure"),
                }
            )
            continue

        relative_note_path = str(result.get("relative_note_path", "")).strip()
        imported_notes.append(
            {
                "title": metadata["title"],
                "citekey": metadata["citekey"],
                "year": metadata["year"],
                "itemType": item_type,
                "relative_note_path": relative_note_path,
                "one_sentence_summary": metadata["one_sentence_summary"],
            }
        )

    review_result: dict[str, Any] | None = None
    if create_review_note:
        review_metadata = {
            "title": resolved_topic,
            "topic": resolved_topic,
            "category": resolved_category,
            "tags": ["materials-review", "zotero-import", topic_tag],
            "topic_overview": _topic_overview(
                topic=resolved_topic,
                category=resolved_category,
                imported_count=len(imported_notes),
                type_counter=type_counter,
                year_counter=year_counter,
            ),
            "next_review_steps": [
                "Group imported papers by task, method family, or material system.",
                "Promote the strongest literature notes into a comparative review narrative.",
                "Track contradictions, missing evidence, and follow-up reading priorities.",
            ],
            "references": imported_notes,
        }
        review_result = writer.invoke(
            {
                "note_type": "review",
                "title": resolved_topic,
                "content": _review_background(
                    topic=resolved_topic,
                    export_path=str(export_path),
                    imported_count=len(imported_notes),
                    type_counter=type_counter,
                    year_counter=year_counter,
                ),
                "metadata_json": json.dumps(review_metadata, ensure_ascii=False),
                "project_name": resolved_topic,
                "category": resolved_category,
                "vault_dir": vault_dir,
                "overwrite": overwrite_existing,
                "review_style": "legacy_materials",
                "filename_style": "title-review",
                "conflict_mode": "error",
            }
        )
        if not review_result.get("ok"):
            return {
                "ok": False,
                "error": review_result.get("error", "Failed to create review note"),
                "export_json_path": str(export_path),
                "topic": resolved_topic,
                "processed_parent_items": limit,
                "imported_count": len(imported_notes),
                "skipped_count": len(skipped_items),
                "bootstrap_result": bootstrap_result,
                "requested_vault_dir": review_result.get("requested_vault_dir", bootstrap_result.get("requested_vault_dir", str(vault_dir or "").strip())),
                "effective_vault_dir": review_result.get("effective_vault_dir", bootstrap_result.get("effective_vault_dir", "")),
                "effective_vault_source": review_result.get("effective_vault_source", bootstrap_result.get("effective_vault_source", "")),
                "fell_back_to_default_vault": review_result.get("fell_back_to_default_vault", bootstrap_result.get("fell_back_to_default_vault", False)),
                "vault_match_status": review_result.get("vault_match_status", bootstrap_result.get("vault_match_status", "exact")),
                "required_skills": review_result.get("required_skills", bootstrap_result.get("required_skills", [])),
                "read_skills": review_result.get("read_skills", bootstrap_result.get("read_skills", [])),
                "missing_required_skills": review_result.get("missing_required_skills", bootstrap_result.get("missing_required_skills", [])),
            }

    logger.info(
        "[obsidian_import_zotero_bbt_json] imported=%s skipped=%s review_created=%s",
        len(imported_notes),
        len(skipped_items),
        bool(review_result and review_result.get("ok")),
    )
    return {
        "ok": True,
        "export_json_path": str(export_path),
        "topic": resolved_topic,
        "category": resolved_category,
        "requested_max_items": max_items,
        "processed_parent_items": limit,
        "imported_count": len(imported_notes),
        "skipped_count": len(skipped_items),
        "imported_notes": imported_notes,
        "skipped_items": skipped_items,
        "review_note_path": review_result.get("note_path", review_result.get("relative_note_path", "")) if review_result else "",
        "materials_root": bootstrap_result.get("materials_root", ""),
        "vault_dir": bootstrap_result.get("vault_dir", ""),
        "requested_vault_dir": bootstrap_result.get("requested_vault_dir", str(vault_dir or "").strip()),
        "effective_vault_dir": bootstrap_result.get("effective_vault_dir", bootstrap_result.get("vault_dir", "")),
        "effective_vault_source": bootstrap_result.get("effective_vault_source", bootstrap_result.get("vault_source", "")),
        "fell_back_to_default_vault": bootstrap_result.get("fell_back_to_default_vault", False),
        "vault_match_status": bootstrap_result.get("vault_match_status", "exact"),
        "required_skills": review_result.get("required_skills", bootstrap_result.get("required_skills", [])) if review_result else bootstrap_result.get("required_skills", []),
        "read_skills": review_result.get("read_skills", bootstrap_result.get("read_skills", [])) if review_result else bootstrap_result.get("read_skills", []),
        "missing_required_skills": review_result.get("missing_required_skills", bootstrap_result.get("missing_required_skills", [])) if review_result else bootstrap_result.get("missing_required_skills", []),
        "created_dirs": bootstrap_result.get("created_dirs", []),
        "created_templates": bootstrap_result.get("created_templates", []),
        "imported_at": datetime.now().isoformat(timespec="seconds"),
    }
