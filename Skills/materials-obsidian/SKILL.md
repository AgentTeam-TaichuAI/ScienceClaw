---
name: materials-obsidian
description: "Write and maintain ScienceClaw materials notes inside an existing Obsidian vault, including literature cards, Chinese review notes, and rewrite passes that overwrite the same review note by default."
---

# materials-obsidian

Use this skill when ScienceClaw output must be written into the user's actual Obsidian vault.

## Scope

Stay inside:

- `Research/Materials/Literature Notes/`
- `Research/Materials/Review Notes/`
- `Research/Materials/Projects/`
- `Research/Materials/Figures/`
- `Research/Materials/Datasets/`
- `Research/Materials/Templates/`

## Strict vault rules

- If the user provides `vault_dir`, pass it through and treat it as strict.
- `vault_match_status=normalized_same_path` means success, not fallback.
- `vault_match_status=fallback_other_path` means failure: do not claim the requested vault was used.
- Rewrites should overwrite the same review note by default instead of creating a timestamped copy.

## Preferred tools

- `obsidian_write_materials_note`
- `obsidian_import_zotero_bbt_json`
- `obsidian_run_zotero_review_agent`
- `obsidian_rewrite_materials_review_note`

## Review-note conventions

For the main Chinese review note:

- `note_type="review"`
- `review_style="survey_cn"`
- `filename_style="title-review"`
- `conflict_mode="error"`

Expected frontmatter fields include:

- `review_bundle_path`
- `source_export_json`
- `review_input_path`
- `review_draft_path`
- `writing_pass`
- `skill_pipeline`

## Companion skills

Use these local skills before the final write when applicable:

1. `zotero-materials-review`
2. `literature-review`
3. `scientific-writing`
4. `obsidian-markdown`

## Safety rules

- Never write outside `Research/Materials/`.
- Do not silently switch vaults.
- Do not create a second manuscript note unless the user explicitly asks for another version.
