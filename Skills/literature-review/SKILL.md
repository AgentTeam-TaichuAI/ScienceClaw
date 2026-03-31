---
name: literature-review
description: "Synthesize local Zotero/Better BibTeX evidence bundles into structured Chinese literature reviews for ScienceClaw. Use when the evidence is already available locally and the task is to organize included, boundary, and excluded papers into a coherent review."
---

# literature-review

Use this skill when the user wants a structured review based on a local Zotero export, bundle, review input JSON, or paper evidence directory.

## Local-first workflow

This ScienceClaw version does not require live database search.

Prefer these local artifacts:

- `review_bundle.json`
- `paper_evidence/*.json`
- `review_input_path`
- imported literature note paths
- current review note frontmatter and body

If those artifacts exist, synthesize directly from them instead of asking for PubMed, arXiv, `gget`, or other online sources.

## Review objectives

Organize the literature into a Chinese survey that makes the evidence traceable:

- distinguish `core_papers`, `boundary_papers`, and `noise_papers`
- summarize main themes rather than listing papers one by one
- preserve limitations and page-based evidence when available
- surface missing PDF coverage and metadata conflicts as warnings

## Preferred section logic

- `摘要`: what was reviewed, from which local source, and what the main conclusions are
- `关键词`: topic plus 3-5 high-signal terms already present in the bundle
- `引言`: background, motivation, and why the topic matters
- `主要研究方向`: thematic grouping of the included papers
- `代表性工作比较与讨论`: compare methods, findings, and evidence strength
- `挑战与争议`: limits of current methods, evidence gaps, unresolved disagreements
- `未来趋势与机会`: what should be added next in Zotero/Obsidian or later writing
- `参考文献`: use the imported note links when available

## Writing constraints

- Keep the synthesis evidence-based and conservative.
- Do not fabricate inclusion/exclusion counts or PDF page quotes.
- Prefer thematic paragraphs over bullet summaries.
- Boundary papers belong in contrast, context, or future-work discussion, not the core claim set.
- Noise papers should stay outside the main argumentative spine unless the user explicitly asks to discuss them.

## Safety rules

- If there is no usable local evidence, say so clearly instead of pretending a review exists.
- If PDFs are missing, mark that the current synthesis relies more heavily on metadata/abstracts.
- Do not require a PDF export step; the final destination is the Obsidian review note unless the user asks for something else.
