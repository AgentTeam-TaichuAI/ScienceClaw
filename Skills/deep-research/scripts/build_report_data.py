#!/usr/bin/env python3
"""
Deep Research report assembler with optional PDF generation.

This helper turns an existing workspace with `sections/*.txt` into a
`report_data.json` file that can be consumed by the builtin PDF template.
It prefers structured metadata from `research_plan.json` /
`research_data/all_references.json`, but can also fall back to the section
files already present in the workspace.

Examples:
    python3 build_report_data.py --base-dir /home/scienceclaw/sessionid

    python3 build_report_data.py \
        --base-dir /home/scienceclaw/sessionid \
        --title "生成模型在材料设计与发现中的应用综述" \
        --pdf-output /home/scienceclaw/sessionid/final_report.pdf
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


SECTION_STEM_RE = re.compile(r"^sec[_-](\d+)(?:[_-](.*))?$", re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,3}\s+(.+?)\s*$", re.MULTILINE)
CITATION_RE = re.compile(r"\[(\d+(?:\s*[,，、]\s*\d+)*)\]")


@dataclass(frozen=True)
class LanguageSpec:
    default_title: str
    report_type: str
    executive_summary: str
    conclusion: str
    references: str
    cover_report_type: str
    cover_date: str
    cover_data_sources: str
    cover_question: str
    disclaimer: str


LANGUAGE_SPECS: dict[str, LanguageSpec] = {
    "zh": LanguageSpec(
        default_title="深度调研报告",
        report_type="深度调研报告",
        executive_summary="执行摘要",
        conclusion="结论与展望",
        references="参考文献",
        cover_report_type="报告类型",
        cover_date="生成日期",
        cover_data_sources="数据来源",
        cover_question="研究问题",
        disclaimer="本报告由 AI 基于现有研究材料自动组装生成，请结合原始文献与实验事实审阅使用。",
    ),
    "en": LanguageSpec(
        default_title="Research Report",
        report_type="Research Report",
        executive_summary="Executive Summary",
        conclusion="Conclusion and Outlook",
        references="References",
        cover_report_type="Report Type",
        cover_date="Generated On",
        cover_data_sources="Data Sources",
        cover_question="Research Question",
        disclaimer="This report was assembled by AI from existing research artifacts and should be reviewed against the original sources.",
    ),
}


SECTION_HINT_RULES: list[tuple[set[str], dict[str, str]]] = [
    ({"abstract", "summary", "executive"}, {"zh": "执行摘要", "en": "Executive Summary"}),
    ({"intro", "introduction", "background", "overview"}, {"zh": "研究背景与问题定义", "en": "Introduction"}),
    ({"literature", "related", "review", "survey"}, {"zh": "文献脉络与代表性工作", "en": "Literature Review"}),
    ({"method", "methods", "methodology", "approach", "framework", "pipeline"}, {"zh": "方法与技术路线", "en": "Methods and Technical Route"}),
    ({"result", "results", "finding", "findings", "analysis", "discussion"}, {"zh": "关键发现与分析", "en": "Findings and Analysis"}),
    ({"uniprot"}, {"zh": "UniProt 功能证据", "en": "UniProt Evidence"}),
    ({"target", "targets"}, {"zh": "靶点与转化线索", "en": "Targets and Translational Signals"}),
    ({"synthesis", "integrated"}, {"zh": "综合分析与启示", "en": "Integrated Synthesis"}),
    ({"challenge", "challenges", "limitation", "limitations"}, {"zh": "挑战与局限", "en": "Challenges and Limitations"}),
    ({"future", "outlook", "trend", "trends"}, {"zh": "未来趋势", "en": "Future Directions"}),
    ({"conclusion", "conclusions"}, {"zh": "结论与展望", "en": "Conclusion and Outlook"}),
    ({"reference", "references", "bibliography"}, {"zh": "参考文献", "en": "References"}),
]


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return _load_json(path)


def _resolve_path(base_dir: Path, raw: str | None) -> Path:
    if not raw:
        return base_dir
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _first_markdown_heading(text: str) -> str:
    match = MARKDOWN_HEADING_RE.search(text)
    if not match:
        return ""
    return _clean_text(match.group(1))


def _is_reference_like_name(path: Path) -> bool:
    lowered = path.stem.lower()
    return any(token in lowered for token in ("reference", "bibliography")) or ("参考文献" in path.stem)


def _split_reference_lines(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        clean = _clean_text(line)
        if not clean or clean.startswith("#"):
            continue
        items.append(clean)
    return items


def _join_authors(authors: Any) -> str:
    if not isinstance(authors, list):
        return ""
    names: list[str] = []
    for entry in authors:
        if isinstance(entry, str):
            name = _clean_text(entry)
        elif isinstance(entry, dict):
            first_name = _clean_text(entry.get("firstName", ""))
            last_name = _clean_text(entry.get("lastName", ""))
            name = " ".join(part for part in (first_name, last_name) if part).strip()
            if not name:
                name = _clean_text(entry.get("name", ""))
        else:
            name = _clean_text(entry)
        if name:
            names.append(name)
    if len(names) > 3:
        return ", ".join(names[:3]) + " et al."
    return ", ".join(names)


def _reference_to_text(item: Any) -> str:
    if isinstance(item, str):
        return _clean_text(item)

    if not isinstance(item, dict):
        return _clean_text(item)

    if item.get("text"):
        return _clean_text(item["text"])
    if item.get("content"):
        return _clean_text(item["content"])

    parts: list[str] = []
    authors = _join_authors(item.get("authors", []))
    title = _clean_text(item.get("title", ""))
    year = _clean_text(item.get("year", ""))
    doi = _clean_text(item.get("doi", ""))
    url = _clean_text(item.get("url", ""))
    citekey = _clean_text(item.get("citekey", ""))

    if authors:
        parts.append(authors)
    if title:
        parts.append(title)
    if year:
        parts.append(f"({year})")
    if doi:
        parts.append(f"DOI: {doi}")
    if url:
        parts.append(url)
    if not parts and citekey:
        parts.append(citekey)

    return ". ".join(part.strip().rstrip(".") for part in parts if part).strip()


def _collect_references(base_dir: Path, sections_dir: Path) -> list[str]:
    references: list[str] = []

    for candidate in (
        base_dir / "research_data" / "all_references.json",
        base_dir / "research_data" / "references.json",
    ):
        payload = _load_json_if_exists(candidate)
        if isinstance(payload, list):
            references = [_reference_to_text(item) for item in payload]
            references = [item for item in references if item]
            if references:
                return references

    review_bundle = _load_json_if_exists(base_dir / "research_data" / "review_bundle.json")
    if isinstance(review_bundle, dict):
        payload = review_bundle.get("references", [])
        if isinstance(payload, list):
            references = [_reference_to_text(item) for item in payload]
            references = [item for item in references if item]
            if references:
                return references

    selected_papers = _load_json_if_exists(base_dir / "research_papers" / "selected_papers.json")
    if isinstance(selected_papers, list):
        references = [_reference_to_text(item) for item in selected_papers]
        references = [item for item in references if item]
        if references:
            return references

    text_candidates = [
        sections_dir / "references.txt",
        sections_dir / "reference.txt",
    ]
    text_candidates.extend(sorted(sections_dir.glob("sec_*reference*.txt")))
    text_candidates.extend(sorted(sections_dir.glob("sec_*references*.txt")))
    text_candidates.extend(sorted(sections_dir.glob("sec_*参考文献*.txt")))

    for candidate in text_candidates:
        if not candidate.exists():
            continue
        references = _split_reference_lines(candidate.read_text(encoding="utf-8"))
        if references:
            return references

    return []


def _load_table_for_section(section_path: Path, sections_dir: Path) -> dict[str, Any] | None:
    candidates: list[Path] = []
    match = SECTION_STEM_RE.match(section_path.stem)
    if match:
        number = match.group(1)
        suffix = (match.group(2) or "").strip("_- ")
        candidates.append(sections_dir / f"table_{number}.json")
        if suffix:
            candidates.append(sections_dir / f"table_{suffix}.json")
    candidates.append(sections_dir / f"table_{section_path.stem}.json")

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.exists():
            continue
        seen.add(candidate)
        payload = _load_json(candidate)
        if not isinstance(payload, dict):
            continue
        headers = payload.get("headers", [])
        rows = payload.get("rows", [])
        if isinstance(headers, list) and isinstance(rows, list):
            return {
                "type": "table",
                "headers": headers,
                "rows": rows,
                "caption": _clean_text(payload.get("caption", "")),
            }
    return None


def _infer_heading_text(stem: str, body: str, language: str, fallback_index: int) -> str:
    spec = LANGUAGE_SPECS.get(language, LANGUAGE_SPECS["en"])
    markdown_heading = _first_markdown_heading(body)
    if markdown_heading and len(markdown_heading) <= 80 and not markdown_heading.startswith("["):
        return markdown_heading

    match = SECTION_STEM_RE.match(stem)
    suffix = (match.group(2) if match else stem) or ""
    cleaned = re.sub(r"[_-]+", " ", suffix).strip()
    lowered = cleaned.lower()
    tokens = {token for token in re.findall(r"[a-z]+", lowered) if token}

    for rule_tokens, titles in SECTION_HINT_RULES:
        if tokens & rule_tokens:
            return titles.get(language, titles["en"])

    if cleaned:
        if re.search(r"[\u4e00-\u9fff]", cleaned):
            return cleaned
        return cleaned.title()

    return f"{spec.report_type} {fallback_index}"


def _sort_key(path: Path) -> tuple[int, str]:
    match = SECTION_STEM_RE.match(path.stem)
    number = int(match.group(1)) if match else 10**9
    return number, path.name.lower()


def _collect_section_files(base_dir: Path, language: str) -> list[tuple[Path, str]]:
    sections_dir = base_dir / "sections"
    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    ordered: list[tuple[Path, str]] = []
    added: set[Path] = set()
    spec = LANGUAGE_SPECS.get(language, LANGUAGE_SPECS["en"])

    summary_path = sections_dir / "executive_summary.txt"
    if summary_path.exists():
        ordered.append((summary_path, spec.executive_summary))
        added.add(summary_path)

    plan = _load_json_if_exists(base_dir / "research_plan.json")
    if isinstance(plan, dict):
        section_map: dict[str, dict[str, Any]] = {}
        structure = plan.get("report_structure", {})
        if isinstance(structure, dict):
            for section in structure.get("sections", []) or []:
                if isinstance(section, dict):
                    key = _clean_text(section.get("subtopic_id", "") or section.get("id", ""))
                    if key:
                        section_map[key] = section

        for subtopic in plan.get("subtopics", []) or []:
            if not isinstance(subtopic, dict):
                continue
            sid = _clean_text(subtopic.get("id", ""))
            if not sid:
                continue
            section_path = sections_dir / f"sec_{sid}.txt"
            if not section_path.exists() or section_path in added:
                continue
            plan_section = section_map.get(sid, {})
            heading = _clean_text(plan_section.get("heading_text", "") or subtopic.get("title", ""))
            if not heading:
                heading = _infer_heading_text(section_path.stem, section_path.read_text(encoding="utf-8"), language, len(ordered) + 1)
            ordered.append((section_path, heading))
            added.add(section_path)

    for section_path in sorted(sections_dir.glob("sec_*.txt"), key=_sort_key):
        if section_path in added or _is_reference_like_name(section_path):
            continue
        body = section_path.read_text(encoding="utf-8")
        heading = _infer_heading_text(section_path.stem, body, language, len(ordered) + 1)
        ordered.append((section_path, heading))
        added.add(section_path)

    conclusion_path = sections_dir / "conclusion.txt"
    if conclusion_path.exists() and conclusion_path not in added:
        ordered.append((conclusion_path, spec.conclusion))

    return ordered


def _extract_max_citation(section_bodies: Iterable[str]) -> int:
    max_citation = 0
    for body in section_bodies:
        for match in CITATION_RE.finditer(body):
            for raw in re.split(r"\s*[,，、]\s*", match.group(1)):
                if raw.isdigit():
                    max_citation = max(max_citation, int(raw))
    return max_citation


def _infer_data_source_summary(base_dir: Path, language: str) -> str:
    sources: list[str] = []
    research_data_dir = base_dir / "research_data"
    if (base_dir / "research_papers").exists():
        sources.append("arXiv / papers" if language == "en" else "论文与候选文献")
    if research_data_dir.exists():
        if any(research_data_dir.glob("web_*.md")):
            sources.append("Web")
        if any(research_data_dir.glob("tooluniverse_*")):
            sources.append("ToolUniverse")
        if (research_data_dir / "paper_evidence").exists():
            sources.append("paper_evidence")
    if not sources:
        sources.append("sections")
    return " / ".join(dict.fromkeys(sources))


def build_report_data(
    base_dir: Path,
    output_path: Path,
    title: str = "",
    subtitle: str = "",
    report_type: str = "",
    language: str = "zh",
) -> tuple[dict[str, Any], list[str]]:
    language = (language or "zh").strip().lower()
    spec = LANGUAGE_SPECS.get(language, LANGUAGE_SPECS["en"])

    plan = _load_json_if_exists(base_dir / "research_plan.json")
    structure = plan.get("report_structure", {}) if isinstance(plan, dict) else {}
    scope = plan.get("scope", {}) if isinstance(plan, dict) else {}
    original_question = _clean_text(plan.get("original_question", "")) if isinstance(plan, dict) else ""

    final_title = (
        _clean_text(title)
        or _clean_text(structure.get("title", "")) if isinstance(structure, dict) else ""
    ) or original_question or spec.default_title
    final_subtitle = _clean_text(subtitle)
    if not final_subtitle and isinstance(structure, dict):
        final_subtitle = _clean_text(structure.get("subtitle", ""))
    final_report_type = _clean_text(report_type) or spec.report_type

    sections_dir = base_dir / "sections"
    references = _collect_references(base_dir, sections_dir)
    section_files = _collect_section_files(base_dir, language)
    if not section_files:
        raise FileNotFoundError(f"No section text files found under: {sections_dir}")

    report: dict[str, Any] = {
        "title": final_title,
        "subtitle": final_subtitle,
        "short_title": final_title[:40],
        "report_type": final_report_type,
        "toc": True,
        "cover_meta": [
            [spec.cover_report_type, final_report_type],
            [spec.cover_date, str(date.today())],
            [spec.cover_data_sources, _infer_data_source_summary(base_dir, language)],
            [spec.cover_question, original_question or final_title],
        ],
        "disclaimer": spec.disclaimer,
        "sections": [],
    }

    section_bodies: list[str] = []
    for index, (section_path, heading_text) in enumerate(section_files, start=1):
        body = _clean_text(section_path.read_text(encoding="utf-8"))
        report["sections"].append(
            {
                "type": "heading",
                "level": 1,
                "number": f"{index}.",
                "text": heading_text,
            }
        )
        report["sections"].append({"type": "text", "body": body})
        section_bodies.append(body)

        table_block = _load_table_for_section(section_path, sections_dir)
        if table_block:
            report["sections"].append(table_block)

    max_citation = _extract_max_citation(section_bodies)
    if references or max_citation > 0:
        report["sections"].append(
            {
                "type": "heading",
                "level": 1,
                "number": f"{len(section_files) + 1}.",
                "text": spec.references,
            }
        )
        report["sections"].append({"type": "references", "items": references})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    warnings: list[str] = []
    if max_citation > len(references):
        warnings.append(
            f"正文最大引用编号为 [{max_citation}]，但仅收集到 {len(references)} 条参考文献。"
        )
    if max_citation > 0 and not references:
        warnings.append("正文包含引用标记，但未找到可用的参考文献列表。")

    if isinstance(scope, dict) and scope.get("domain") and not report["cover_meta"][2][1]:
        report["cover_meta"][2][1] = _clean_text(scope.get("domain", ""))

    return report, warnings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble report_data.json from an existing deep-research workspace.")
    parser.add_argument("--base-dir", default=".", help="Workspace root that contains sections/, research_data/, etc.")
    parser.add_argument("--output", default="report_data.json", help="Output report_data.json path. Relative paths resolve under --base-dir.")
    parser.add_argument("--title", default="", help="Override report title.")
    parser.add_argument("--subtitle", default="", help="Override report subtitle.")
    parser.add_argument("--report-type", default="", help="Override report type shown on cover/header.")
    parser.add_argument("--language", default="zh", help="Report language, e.g. zh or en.")
    parser.add_argument("--pdf-output", default="", help="Optional final PDF path. When set, also runs generate_report.py.")
    parser.add_argument("--generator-script", default="generate_report.py", help="Path to generate_report.py. Relative paths resolve under --base-dir.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    base_dir = _resolve_path(Path.cwd(), args.base_dir)
    output_path = _resolve_path(base_dir, args.output)

    report, warnings = build_report_data(
        base_dir=base_dir,
        output_path=output_path,
        title=args.title,
        subtitle=args.subtitle,
        report_type=args.report_type,
        language=args.language,
    )

    section_count = sum(1 for item in report["sections"] if item.get("type") == "heading")
    body_chars = sum(len(item.get("body", "")) for item in report["sections"] if item.get("type") == "text")
    reference_count = sum(len(item.get("items", [])) for item in report["sections"] if item.get("type") == "references")

    print(f"Report data generated: {output_path}")
    print(f"  Title      : {report['title']}")
    print(f"  Sections   : {section_count}")
    print(f"  Characters : {body_chars}")
    print(f"  Est. pages : {body_chars // 500}")
    print(f"  References : {reference_count}")
    for warning in warnings:
        print(f"  WARNING    : {warning}")

    if args.pdf_output:
        pdf_output = _resolve_path(base_dir, args.pdf_output)
        generator_script = _resolve_path(base_dir, args.generator_script)
        if not generator_script.exists():
            raise FileNotFoundError(f"PDF generator not found: {generator_script}")

        pdf_output.parent.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(generator_script), str(output_path), str(pdf_output)]
        print("Running PDF generator:")
        print("  " + " ".join(command))
        subprocess.run(command, check=True)

        if not pdf_output.exists() or pdf_output.stat().st_size <= 0:
            raise RuntimeError(f"PDF generation finished without creating a valid file: {pdf_output}")

        print(f"PDF generated: {pdf_output}")
        print(f"  Size       : {pdf_output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
