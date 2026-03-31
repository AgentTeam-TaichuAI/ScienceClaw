---
name: zotero-materials-review
description: "Run ScienceClaw's local Zotero -> evidence bundle -> Chinese review -> Obsidian workflow using Better BibTeX JSON and attached PDFs, then support continued rewrites of the same review note."
---

# zotero-materials-review

Use this skill when the user provides a Zotero / Better BibTeX JSON export and wants a real review workflow instead of only imported literature cards.

## Main path

Prefer the unified tool:

- `obsidian_run_zotero_review_agent`

Use the lower-level tools only when the user explicitly asks for a partial workflow:

- `obsidian_import_zotero_bbt_json` for literature-note import only
- `obsidian_build_zotero_review_bundle` for bundle rebuild only

## Required local skill order

Before the final review note write or rewrite, read these skills in order:

1. `zotero-materials-review`
2. `literature-review`
3. `scientific-writing`
4. `obsidian-markdown`
5. `materials-obsidian`

## End-to-end workflow

1. Validate the uploaded Better BibTeX JSON.
2. Build the local evidence bundle with PDF-first extraction.
3. Import/update literature notes in Obsidian.
4. Read `review_input_path` and `review_draft_path` when available.
5. Use `literature-review` for evidence organization.
6. Use `scientific-writing` to polish the Chinese prose.
7. Use `obsidian-markdown` to normalize the final markdown.
8. Write back to the same review note with `obsidian_write_materials_note`.

## Rewrite workflow

When the user asks for "继续改写", "更像论文", "GB/T 7714", or similar:

- prefer `obsidian_rewrite_materials_review_note`
- reuse the most recent review note context when available
- overwrite the same note by default

## Review note target

The canonical review note path is:

- `Research/Materials/Review Notes/<topic> - review.md`

Do not default to timestamped copies unless the user explicitly asks for "另存一版".

## Safety rules

- Prefer local PDF/HTML/full-text evidence over mismatched `abstractNote`.
- Preserve `doi`, `citekey`, `zotero_key`, and imported literature-note links.
- Do not switch to online skill discovery unless the user explicitly asks to search the web for similar skills.
