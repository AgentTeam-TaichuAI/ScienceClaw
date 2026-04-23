import base64
import json
import logging
import os
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

__tool_meta__ = {
    "category": "Obsidian",
    "subcategory": "Review Bundle",
    "tags": ["obsidian", "zotero", "review", "materials"],
}

_SKIP_ITEM_TYPES = {"attachment", "note"}
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_HOST_BRIDGE_CANDIDATES = [
    "http://127.0.0.1:8765",
    "http://host.docker.internal:8765",
]
_TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "applications",
    "approach",
    "for",
    "framework",
    "in",
    "materials",
    "material",
    "models",
    "model",
    "of",
    "on",
    "review",
    "study",
    "survey",
    "the",
    "to",
    "using",
    "with",
}
_AI_KEYWORDS = {
    "agent",
    "agents",
    "diffusion",
    "gan",
    "generative",
    "language",
    "llm",
    "multimodal",
    "nlp",
    "transformer",
}
_MATERIALS_KEYWORDS = {
    "adsorption",
    "alloy",
    "alloys",
    "catalysis",
    "chemistry",
    "crystal",
    "discovery",
    "inorganic",
    "materials",
    "material",
}
_NOISE_KEYWORDS = {
    "architectural",
    "category",
    "classification",
    "cluster",
    "fine-tuning",
    "images",
    "layout",
    "prototype",
    "space",
}
_SECTION_HINTS = {
    "llm": "大语言模型与科研助手",
    "generative": "生成模型驱动的材料设计与发现",
    "multimodal": "多模态与图结构建模",
    "benchmark": "评测、基准与方法边界",
    "cross_domain": "跨学科迁移与工具增强",
}


def _contains_any(text: str, keywords: tuple[str, ...] | list[str] | set[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = text.replace("\x00", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", _clean_text(text)).strip()


def _creator_names(creators: Any) -> list[str]:
    names: list[str] = []
    for creator in creators or []:
        if not isinstance(creator, dict):
            continue
        if creator.get("creatorType") not in (None, "", "author"):
            continue
        first_name = str(creator.get("firstName", "")).strip()
        last_name = str(creator.get("lastName", "")).strip()
        name = " ".join(part for part in [first_name, last_name] if part)
        if not name:
            name = str(creator.get("name", "")).strip()
        if name:
            names.append(name)
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


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())


def _title_keywords(title: str) -> list[str]:
    words: list[str] = []
    for word in _tokenize(title):
        if word in _TITLE_STOPWORDS:
            continue
        if word not in words:
            words.append(word)
    return words[:8]


def _keyword_coverage(keywords: list[str], text: str) -> float:
    if not keywords:
        return 0.0
    haystack = text.lower()
    hits = sum(1 for keyword in keywords if keyword in haystack)
    return hits / len(keywords)


def _first_sentence(text: str) -> str:
    cleaned = _normalize_whitespace(text)
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned, maxsplit=1)
    sentence = parts[0].strip()
    if len(sentence) > 320:
        return sentence[:317].rstrip() + "..."
    return sentence


def _safe_slug(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", str(value or ""), flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-_")
    return slug or fallback


def _normalize_category(value: str, topic: str) -> str:
    explicit = str(value or "").strip()
    topic_text = str(topic or "").strip()
    if not explicit:
        return topic_text
    explicit_slug = _safe_slug(explicit, "")
    topic_slug = _safe_slug(topic_text, "") if topic_text else ""
    if explicit_slug in {"material", "materials"} and topic_slug and explicit_slug != topic_slug:
        return topic_text
    return explicit


def _output_root(export_path: Path) -> Path:
    if export_path.parent.name.lower() in {"zotero", "uploads", "input", "inputs"}:
        return export_path.parent.parent
    return export_path.parent


def _research_run_dir(root_dir: Path, topic: str, category: str) -> Path:
    research_root = root_dir / "research_data"
    topic_slug = _safe_slug(topic, "materials-topic")
    category_slug = _safe_slug(category, "materials-category") if str(category or "").strip() else ""
    if category_slug and category_slug != topic_slug:
        return research_root / category_slug / topic_slug
    return research_root / topic_slug


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


def _host_read_file(path: str, timeout: float = 60.0) -> dict[str, Any]:
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


def _cache_host_attachment(
    original_path: str,
    cache_dir: Path,
    citekey: str,
) -> tuple[Path | None, dict[str, Any]]:
    result = _host_read_file(original_path)
    data = result.get("data", {}) if isinstance(result, dict) else {}
    if not result.get("ok"):
        return None, {
            "ok": False,
            "source": "host_bridge",
            "error": data.get("error", "Failed to read host file"),
            "bridge_url": result.get("bridge_url", ""),
        }

    suffix = str(data.get("suffix", "") or Path(original_path).suffix or "").lower()
    cache_name = f"{_safe_slug(citekey, 'attachment')}{suffix or '.bin'}"
    cache_path = cache_dir / cache_name
    raw = base64.b64decode(str(data.get("content_base64", "")).encode("ascii"))
    cache_path.write_bytes(raw)
    return cache_path, {
        "ok": True,
        "source": "host_bridge",
        "bridge_url": result.get("bridge_url", ""),
        "path": str(cache_path),
        "original_path": original_path,
    }


def _resolve_attachment_path(path_value: str, cache_dir: Path, citekey: str) -> tuple[Path | None, dict[str, Any]]:
    raw = str(path_value or "").strip()
    if not raw:
        return None, {"ok": False, "source": "missing", "error": "Attachment path missing"}

    candidate = Path(raw).expanduser()
    if candidate.is_absolute() and candidate.exists() and candidate.is_file():
        return candidate, {"ok": True, "source": "local_path", "path": str(candidate)}

    if os.name != "nt" and _WINDOWS_DRIVE_RE.match(raw):
        return _cache_host_attachment(raw, cache_dir, citekey)

    if candidate.exists() and candidate.is_file():
        return candidate.resolve(), {"ok": True, "source": "local_path", "path": str(candidate.resolve())}

    return None, {
        "ok": False,
        "source": "unavailable",
        "error": f"Attachment path not accessible: {raw}",
    }


def _strip_html(html_text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html_text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    return _clean_text(text)


def _extract_html_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return _strip_html(raw)


def _split_pages(raw_text: str) -> list[str]:
    pages = [part.strip() for part in raw_text.split("\f")]
    return [page for page in pages if page]


def _extract_pdf_pages_pdftotext(path: Path) -> tuple[list[str], str]:
    completed = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "").strip() or "pdftotext failed")
    pages = _split_pages(completed.stdout)
    if not pages:
        raise RuntimeError("pdftotext returned no readable text")
    return pages, "pdftotext"


def _extract_pdf_pages_pymupdf(path: Path) -> tuple[list[str], str]:
    import fitz  # type: ignore

    doc = fitz.open(path)
    try:
        pages = [_clean_text(page.get_text("text", sort=True)) for page in doc]
    finally:
        doc.close()
    pages = [page for page in pages if page]
    if not pages:
        raise RuntimeError("PyMuPDF returned no readable text")
    return pages, "pymupdf"


def _extract_pdf_pages_pdfplumber(path: Path) -> tuple[list[str], str]:
    import pdfplumber  # type: ignore

    with pdfplumber.open(path) as pdf:
        pages = [_clean_text(page.extract_text() or "") for page in pdf.pages]
    pages = [page for page in pages if page]
    if not pages:
        raise RuntimeError("pdfplumber returned no readable text")
    return pages, "pdfplumber"


def _extract_pdf_pages(path: Path) -> tuple[list[str], str, list[str]]:
    errors: list[str] = []
    for extractor in (
        _extract_pdf_pages_pdftotext,
        _extract_pdf_pages_pymupdf,
        _extract_pdf_pages_pdfplumber,
    ):
        try:
            pages, method = extractor(path)
            return pages, method, errors
        except Exception as exc:  # pragma: no cover - extractor fallback
            errors.append(f"{extractor.__name__}: {exc}")
    return [], "", errors


def _find_page_excerpt(
    pages: list[str],
    patterns: list[re.Pattern[str]],
    fallback_chars: int = 1400,
) -> tuple[str, list[int]]:
    for index, page in enumerate(pages, start=1):
        for pattern in patterns:
            match = pattern.search(page)
            if match:
                start = max(match.start() - 200, 0)
                end = min(match.end() + 1200, len(page))
                return page[start:end].strip(), [index]
    merged = _clean_text("\n\n".join(pages[:2]))
    return merged[:fallback_chars].strip(), [1] if merged else []


def _extract_limitations(text: str) -> str:
    lowered = text.lower()
    markers = [
        "limitation",
        "limitations",
        "however",
        "future work",
        "challenge",
        "challenges",
    ]
    for marker in markers:
        idx = lowered.find(marker)
        if idx >= 0:
            return text[idx: idx + 900].strip()
    return ""


def _select_section_hint(title: str, text: str) -> str:
    title_lower = title.lower()
    lowered = f"{title}\n{text}".lower()
    if any(token in title_lower for token in ("benchmark", "bench")):
        return _SECTION_HINTS["benchmark"]
    if any(token in title_lower for token in ("generative", "gan", "diffusion", "mattergen", "design framework")):
        return _SECTION_HINTS["generative"]
    if any(token in title_lower for token in ("multimodal", "graph", "adsorption", "catalysis")):
        return _SECTION_HINTS["multimodal"]
    if any(token in title_lower for token in ("agent", "autonomous", "assistant", "pilot", "language", "llm", "nlp")):
        return _SECTION_HINTS["llm"]
    if any(token in title_lower for token in ("chemistry", "tool", "workflow")):
        return _SECTION_HINTS["cross_domain"]
    if any(token in lowered for token in ("benchmark", "bench", "evaluation")):
        return _SECTION_HINTS["benchmark"]
    if any(token in lowered for token in ("generative", "gan", "diffusion", "mattergen", "design framework")):
        return _SECTION_HINTS["generative"]
    if any(token in lowered for token in ("multimodal", "graph", "adsorption", "catalysis")):
        return _SECTION_HINTS["multimodal"]
    if any(token in lowered for token in ("agent", "autonomous", "assistant", "pilot", "language", "llm", "nlp")):
        return _SECTION_HINTS["llm"]
    if any(token in lowered for token in ("chemistry", "tool", "workflow")):
        return _SECTION_HINTS["cross_domain"]
    return _SECTION_HINTS["generative"]


def _detect_metadata_conflict(title: str, abstract: str, fulltext: str) -> tuple[bool, str]:
    abstract_clean = _normalize_whitespace(abstract)
    if not abstract_clean:
        return False, "abstract_missing"

    keywords = _title_keywords(title)
    abstract_coverage = _keyword_coverage(keywords, abstract_clean)
    fulltext_coverage = _keyword_coverage(keywords, fulltext)
    abstract_noise_hits = sum(1 for keyword in _NOISE_KEYWORDS if keyword in abstract_clean.lower())

    if abstract_coverage < 0.34 and len(abstract_clean) > 240:
        if fulltext and fulltext_coverage >= 0.5:
            return True, "abstract_keywords_do_not_match_title_but_fulltext_matches"
        if abstract_noise_hits >= 3:
            return True, "abstract_semantics_deviate_from_title"
    return False, "no_conflict_detected"


def _classify_relevance(title: str, abstract: str, fulltext: str, topic_seed: str, policy: str) -> tuple[str, str]:
    lowered = f"{title}\n{abstract}\n{fulltext}".lower()
    title_lower = title.lower()
    seed_lower = topic_seed.lower()

    ai_hits = sum(1 for keyword in _AI_KEYWORDS if keyword in lowered)
    materials_hits = sum(1 for keyword in _MATERIALS_KEYWORDS if keyword in lowered)
    noise_hits = sum(1 for keyword in _NOISE_KEYWORDS if keyword in lowered)
    generative_hits = sum(1 for keyword in ("generative", "gan", "diffusion", "mattergen", "design") if keyword in lowered)
    llm_hits = sum(1 for keyword in ("language", "llm", "nlp", "agent") if keyword in lowered)

    title_materials_hits = sum(1 for keyword in _MATERIALS_KEYWORDS if keyword in title_lower)
    title_noise_hits = sum(1 for keyword in _NOISE_KEYWORDS if keyword in title_lower)
    title_generative_hits = sum(
        1 for keyword in ("generative", "gan", "diffusion", "mattergen", "design") if keyword in title_lower
    )
    title_llm_hits = sum(1 for keyword in ("language", "llm", "nlp", "agent") if keyword in title_lower)
    title_review_hits = sum(1 for keyword in ("review", "survey", "benchmark", "bench") if keyword in title_lower)

    is_generative_topic = _contains_any(seed_lower, ("生成模型", "generative", "diffusion", "gan"))
    is_llm_topic = _contains_any(seed_lower, ("大语言模型", "llm", "language"))

    if title_noise_hits >= 1 and title_materials_hits == 0:
        return "noise", "title_is_off_topic_for_materials_review"

    if _contains_any(title_lower, ("parameter-efficient fine-tuning", "fine-tuning")) and title_materials_hits == 0:
        return "boundary", "foundation_methodology_relevant_but_not_materials_specific"

    if is_generative_topic:
        if title_materials_hits >= 1 and title_generative_hits >= 1:
            return "core", "materials_specific_generative_paper"
        if title_materials_hits >= 1 and title_llm_hits >= 1:
            return "boundary", "materials_specific_llm_paper_related_to_generative_review"
        if title_review_hits >= 1 and _contains_any(title_lower, ("chemistry", "materials")):
            return "boundary", "survey_or_benchmark_related_to_topic"
        if materials_hits >= 1 and generative_hits >= 1:
            return "core", "fulltext_indicates_materials_generative_relevance"
        if materials_hits >= 1 and (llm_hits >= 1 or ai_hits >= 2):
            return "boundary", "materials_ai_paper_related_but_not_generative_core"
        if policy == "wide" and ai_hits >= 2 and materials_hits >= 1:
            return "boundary", "kept_under_wide_policy"
        return "noise", "insufficient_alignment_with_generative_materials_topic"

    if is_llm_topic:
        if title_materials_hits >= 1 and title_llm_hits >= 1:
            return "core", "materials_specific_llm_paper"
        if title_materials_hits >= 1 and title_generative_hits >= 1:
            return "boundary", "generative_materials_paper_related_to_llm_review"
        if title_review_hits >= 1 and _contains_any(title_lower, ("chemistry", "materials")):
            return "boundary", "survey_or_benchmark_related_to_topic"
        if materials_hits >= 1 and llm_hits >= 1:
            return "core", "fulltext_indicates_materials_llm_relevance"
        if materials_hits >= 1 and ai_hits >= 2:
            return "boundary", "materials_ai_paper_related_but_not_llm_core"
        if policy == "wide" and ai_hits >= 2 and materials_hits >= 1:
            return "boundary", "kept_under_wide_policy"
        return "noise", "insufficient_alignment_with_llm_materials_topic"

    score = materials_hits * 3 + ai_hits * 2 + generative_hits + llm_hits - noise_hits * 2
    if materials_hits >= 1 and (llm_hits >= 1 or generative_hits >= 1):
        label = "core" if score >= 6 else "boundary"
    elif score >= 4:
        label = "boundary"
    else:
        label = "noise"

    if policy == "wide" and label == "noise" and score >= 2:
        label = "boundary"

    reason = (
        f"materials_hits={materials_hits}, ai_hits={ai_hits}, generative_hits={generative_hits}, "
        f"llm_hits={llm_hits}, noise_hits={noise_hits}, title_materials_hits={title_materials_hits}, "
        f"title_generative_hits={title_generative_hits}, title_llm_hits={title_llm_hits}, score={score}"
    )
    return label, reason


def _suggest_title(topic_seed: str, papers: list[dict[str, Any]]) -> str:
    seed = str(topic_seed or "").strip()
    if seed:
        if seed.endswith("综述") and any(term in seed for term in ("材料", "生成模型", "大语言模型")):
            return seed
        if "大语言模型" in seed:
            return "大语言模型在材料科学中的应用综述"
        if "生成模型" in seed:
            return "生成模型在材料设计与发现中的应用综述"

    lowered_titles = "\n".join(str(paper.get("title", "")) for paper in papers).lower()
    llm_hits = sum(1 for token in ("language", "llm", "nlp", "agent") if token in lowered_titles)
    generative_hits = sum(1 for token in ("generative", "gan", "diffusion", "design") if token in lowered_titles)
    materials_hits = sum(1 for token in ("materials", "material", "alloy", "chemistry", "discovery") if token in lowered_titles)

    if llm_hits >= generative_hits and materials_hits:
        return "大语言模型在材料科学中的应用综述"
    if generative_hits or materials_hits:
        return "生成模型在材料设计与发现中的应用综述"
    if seed:
        return f"{seed}领域研究综述"
    return "材料智能研究综述"


def _resolve_max_workers(limit: int, requested: int) -> int:
    if limit <= 1:
        return 1

    if requested > 0:
        return min(requested, limit)

    cpu_bound_default = os.cpu_count() or 4
    return max(1, min(limit, cpu_bound_default, 8))


def _truncate(text: str, length: int) -> str:
    clean = _clean_text(text)
    if len(clean) <= length:
        return clean
    return clean[: length - 3].rstrip() + "..."


def _extract_attachment_candidates(item: dict[str, Any], suffixes: set[str]) -> list[str]:
    candidates: list[str] = []
    for attachment in item.get("attachments", []) or []:
        if not isinstance(attachment, dict):
            continue
        for key in ("path", "url"):
            value = str(attachment.get(key, "")).strip()
            if value and Path(value).suffix.lower() in suffixes:
                candidates.append(value)
    return candidates


def _build_paper_evidence(
    item: dict[str, Any],
    topic_seed: str,
    cache_dir: Path,
    relevance_policy: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    title = str(item.get("title", "")).strip() or "Untitled"
    citekey = str(item.get("citationKey", "")).strip() or _safe_slug(title, "untitled")
    abstract = _clean_text(item.get("abstractNote", ""))

    pdf_candidates = _extract_attachment_candidates(item, {".pdf"})
    html_candidates = _extract_attachment_candidates(item, {".html", ".htm", ".txt"})

    pdf_path: Path | None = None
    pdf_source: dict[str, Any] | None = None
    for candidate in pdf_candidates:
        pdf_path, pdf_source = _resolve_attachment_path(candidate, cache_dir, citekey)
        if pdf_path:
            break

    html_path: Path | None = None
    html_source: dict[str, Any] | None = None
    for candidate in html_candidates:
        html_path, html_source = _resolve_attachment_path(candidate, cache_dir, f"{citekey}-html")
        if html_path:
            break

    page_texts: list[str] = []
    extraction_method = ""
    extraction_errors: list[str] = []
    if pdf_path:
        page_texts, extraction_method, extraction_errors = _extract_pdf_pages(pdf_path)

    fulltext = _clean_text("\n\n".join(page_texts))
    if not fulltext and html_path:
        try:
            fulltext = _extract_html_text(html_path)
            extraction_method = extraction_method or "html"
        except Exception as exc:
            extraction_errors.append(f"html_extract: {exc}")

    intro_excerpt, intro_pages = _find_page_excerpt(
        page_texts or [fulltext],
        [
            re.compile(r"(?im)^\s*(1\.?\s+)?introduction\b"),
            re.compile(r"(?im)^\s*introduction\b"),
            re.compile(r"(?im)^\s*background\b"),
        ],
    )
    methods_excerpt, methods_pages = _find_page_excerpt(
        page_texts or [fulltext],
        [
            re.compile(r"(?im)^\s*(2\.?\s+)?(methods?|methodology|approach)\b"),
            re.compile(r"(?im)^\s*(our approach|framework)\b"),
        ],
    )
    findings_excerpt, findings_pages = _find_page_excerpt(
        page_texts or [fulltext],
        [
            re.compile(r"(?im)^\s*(results?|discussion|conclusion)\b"),
            re.compile(r"(?im)^\s*(4\.?\s+results?|5\.?\s+discussion)\b"),
        ],
    )
    limitations_excerpt = _extract_limitations(fulltext or findings_excerpt or intro_excerpt)

    metadata_conflict, conflict_reason = _detect_metadata_conflict(title, abstract, fulltext)
    relevance_label, relevance_reason = _classify_relevance(title, abstract, fulltext, topic_seed, relevance_policy)
    effective_summary_source = fulltext if metadata_conflict and fulltext else abstract
    section_hint = _select_section_hint(title, fulltext or abstract)

    evidence = {
        "title": title,
        "authors": _creator_names(item.get("creators", [])),
        "year": _extract_year(item),
        "doi": str(item.get("DOI", "")).strip(),
        "citekey": citekey,
        "attachment_pdf_path": str(pdf_path) if pdf_path else "",
        "attachment_html_path": str(html_path) if html_path else "",
        "abstract_from_json": abstract,
        "fulltext_excerpt": _truncate(intro_excerpt or fulltext, 1800),
        "methods_summary": _truncate(methods_excerpt or effective_summary_source, 1400),
        "key_findings": _truncate(findings_excerpt or effective_summary_source, 1400),
        "limitations": _truncate(limitations_excerpt, 1200),
        "relevance_label": relevance_label,
        "relevance_reason": relevance_reason,
        "metadata_conflict": metadata_conflict,
        "metadata_conflict_reason": conflict_reason,
        "evidence_pages": [
            {
                "section": "introduction",
                "pages": intro_pages,
            },
            {
                "section": "methods",
                "pages": methods_pages,
            },
            {
                "section": "findings",
                "pages": findings_pages,
            },
        ],
        "preferred_summary_source": "fulltext" if metadata_conflict and fulltext else ("abstract" if abstract else "fulltext"),
        "one_sentence_summary": _first_sentence(effective_summary_source or title),
        "section_hint": section_hint,
        "source_diagnostics": {
            "pdf_source": pdf_source or {"ok": False, "source": "missing", "error": "No PDF attachment found"},
            "html_source": html_source or {"ok": False, "source": "missing", "error": "No HTML/TXT attachment found"},
            "extraction_method": extraction_method,
            "extraction_errors": extraction_errors,
            "pdf_unavailable": not bool(pdf_path and page_texts),
        },
    }
    reference = {
        "title": title,
        "citekey": citekey,
        "year": evidence["year"],
        "doi": evidence["doi"],
        "relevance_label": relevance_label,
        "metadata_conflict": metadata_conflict,
        "section_hint": section_hint,
    }
    return evidence, reference


def _bundle_lists(papers: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    return [
        {
            "title": paper["title"],
            "citekey": paper["citekey"],
            "year": paper["year"],
            "doi": paper["doi"],
            "section_hint": paper["section_hint"],
            "one_sentence_summary": paper["one_sentence_summary"],
            "relevance_reason": paper["relevance_reason"],
            "metadata_conflict": paper["metadata_conflict"],
        }
        for paper in papers
        if paper["relevance_label"] == label
    ]


@tool
def obsidian_build_zotero_review_bundle(
    export_json_path: str,
    topic: str = "",
    category: str = "",
    language: str = "zh",
    prefer_pdf_fulltext: bool = True,
    relevance_policy: str = "balanced",
    max_items: int = 0,
    max_workers: int = 0,
) -> dict:
    """Build a structured evidence bundle from a Zotero/Better BibTeX export.

    The bundle consolidates JSON metadata, local Zotero attachments, PDF/HTML
    text extraction, relevance grading, and metadata-conflict detection into a
    stable set of JSON files that can be used to write a Chinese survey note.
    """
    logger.info(
        "[obsidian_build_zotero_review_bundle] export_json_path=%r topic=%r language=%r prefer_pdf_fulltext=%s relevance_policy=%r max_items=%s max_workers=%s",
        export_json_path,
        topic,
        language,
        prefer_pdf_fulltext,
        relevance_policy,
        max_items,
        max_workers,
    )

    export_path = Path(export_json_path).expanduser()
    if not export_path.is_absolute():
        export_path = Path.cwd() / export_path
    if not export_path.exists():
        return {"ok": False, "error": f"Export JSON not found: {export_path}"}

    try:
        payload = _load_json(export_path)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON: {exc}"}

    items = payload.get("items", [])
    if not isinstance(items, list):
        return {"ok": False, "error": "Expected `items` to be a list in Better BibTeX export"}

    root_dir = _output_root(export_path)
    topic_seed = topic.strip() or export_path.stem
    resolved_category = _normalize_category(category, topic_seed)
    research_data_dir = _research_run_dir(root_dir, topic_seed, resolved_category)
    evidence_dir = research_data_dir / "paper_evidence"
    cache_dir = research_data_dir / "attachments_cache"
    research_data_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    parent_items = [item for item in items if isinstance(item, dict) and item.get("itemType") not in _SKIP_ITEM_TYPES]
    limit = len(parent_items) if max_items <= 0 else min(max_items, len(parent_items))
    worker_count = _resolve_max_workers(limit, max_workers)

    evidences: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    section_counter: Counter[str] = Counter()

    indexed_results: list[tuple[dict[str, Any], dict[str, Any]] | None] = [None] * limit
    selected_items = parent_items[:limit]

    if worker_count == 1:
        for index, item in enumerate(selected_items):
            indexed_results[index] = _build_paper_evidence(
                item=item,
                topic_seed=topic_seed,
                cache_dir=cache_dir,
                relevance_policy=relevance_policy,
            )
    else:
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="zotero-review") as executor:
            futures = {
                executor.submit(
                    _build_paper_evidence,
                    item=item,
                    topic_seed=topic_seed,
                    cache_dir=cache_dir,
                    relevance_policy=relevance_policy,
                ): index
                for index, item in enumerate(selected_items)
            }
            for future in as_completed(futures):
                index = futures[future]
                indexed_results[index] = future.result()

    for result in indexed_results:
        if result is None:
            raise RuntimeError("Paper evidence build did not complete for every selected item")

        evidence, reference = result
        if not prefer_pdf_fulltext and evidence.get("abstract_from_json"):
            evidence["preferred_summary_source"] = "abstract"
        section_counter[evidence["section_hint"]] += 1
        evidence_path = evidence_dir / f"{_safe_slug(evidence['citekey'], 'paper')}.json"
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence["evidence_json_path"] = str(evidence_path)
        evidences.append(evidence)
        references.append(reference)

    suggested_title = _suggest_title(topic_seed, evidences)
    metadata_conflicts = [
        {
            "title": evidence["title"],
            "citekey": evidence["citekey"],
            "reason": evidence["metadata_conflict_reason"],
        }
        for evidence in evidences
        if evidence["metadata_conflict"]
    ]
    section_hints = [
        {
            "heading": heading,
            "paper_count": count,
        }
        for heading, count in section_counter.most_common()
    ]

    bundle = {
        "suggested_title": suggested_title,
        "topic_seed": topic_seed,
        "category": resolved_category,
        "language": language,
        "core_papers": _bundle_lists(evidences, "core"),
        "boundary_papers": _bundle_lists(evidences, "boundary"),
        "noise_papers": _bundle_lists(evidences, "noise"),
        "metadata_conflicts": metadata_conflicts,
        "section_hints": section_hints,
        "references": references,
        "source_paths": {
            "export_json_path": str(export_path),
            "review_bundle_path": str(research_data_dir / "review_bundle.json"),
            "paper_evidence_dir": str(evidence_dir),
            "attachments_cache_dir": str(cache_dir),
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    bundle_path = research_data_dir / "review_bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "suggested_title": suggested_title,
        "topic": topic_seed,
        "category": resolved_category,
        "export_json_path": str(export_path),
        "review_bundle_path": str(bundle_path),
        "paper_evidence_dir": str(evidence_dir),
        "attachments_cache_dir": str(cache_dir),
        "processed_parent_items": limit,
        "max_workers_used": worker_count,
        "core_count": len(bundle["core_papers"]),
        "boundary_count": len(bundle["boundary_papers"]),
        "noise_count": len(bundle["noise_papers"]),
        "metadata_conflict_count": len(metadata_conflicts),
        "section_hints": section_hints,
    }
