---
name: scientific-writing
description: "Polish local review drafts into publication-style Chinese scientific prose for ScienceClaw's Zotero/Obsidian workflow. Use when refining a generated review note, revising structure, tightening wording, or adapting citation style without adding external web research."
---

# scientific-writing

Use this skill when ScienceClaw already has a local draft, review note, or evidence package and the task is to turn it into more academic, paragraph-based Chinese prose.

## Scope

This skill is local-first and evidence-first:

- Prefer existing `review_input_path`, `review_draft_path`, `review_bundle_path`, and the current review note body.
- Do not require `research-lookup`, `scientific-schematics`, or any other external skill.
- Do not introduce new factual claims or citations that are not supported by the local bundle or note.

## Core rules

- Final output must be full paragraphs, not outline bullets.
- Preserve evidence-backed claims, limitations, and paper links already present in the local draft.
- If the user asks for "更像论文", "更学术", "科研文体", or similar, tighten wording, reduce口语化表达, and strengthen transitions between paragraphs.
- If the user asks for `GB/T 7714`, rewrite the reference section into numbered Chinese-style entries, but do not fabricate missing bibliographic fields.
- Keep the language Chinese unless the user explicitly asks otherwise.

## Input priority

When multiple local inputs exist, use them in this order:

1. `review_input_path` JSON
2. `review_draft_path` markdown
3. current review note body
4. `review_bundle_path` as supporting evidence only

## Preferred output shape

Keep the rewritten review compatible with Obsidian and `survey_cn` review notes:

- `# 标题`
- `## 摘要`
- `## 关键词`
- `## 引言`
- `## 主要研究方向`
- `## 代表性工作比较与讨论`
- `## 挑战与争议`
- `## 未来趋势与机会`
- `## 结论`
- `## 参考文献`

## Safety rules

- Never overwrite the requested review note with content unrelated to the supplied topic.
- Do not silently drop the `参考文献` section.
- Do not invent experiments, datasets, page numbers, or PDF evidence.
- When evidence is incomplete, keep the statement conservative and note the limitation instead of guessing.
