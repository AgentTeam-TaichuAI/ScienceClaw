---
name: obsidian-markdown
description: Create and normalize Obsidian-compatible markdown for ScienceClaw review notes, including frontmatter, wikilinks, headings, callouts, and reference sections.
---

# obsidian-markdown

Use this skill when the final output will be written into Obsidian.

## Review-note rules

- Keep valid YAML frontmatter at the top.
- Preserve tracking fields such as `review_bundle_path`, `source_export_json`, `review_input_path`, `review_draft_path`, `writing_pass`, and `skill_pipeline`.
- Use one `# 标题` heading at most once.
- Use `##` headings for the main review sections.
- Keep imported literature-note references as Obsidian wikilinks when possible.

## Preferred structure

For ScienceClaw review notes, keep this section order unless the user explicitly asks for another structure:

- `## 摘要`
- `## 关键词`
- `## 引言`
- `## 主要研究方向`
- `## 代表性工作比较与讨论`
- `## 挑战与争议`
- `## 未来趋势与机会`
- `## 结论`
- `## 参考文献`

## Formatting rules

- Use `[[note]]` links for internal vault references.
- Use standard markdown links only for external URLs.
- Avoid decorative callouts unless they add value; remove transient generation callouts from the final polished note when the user asks for a paper-like style.
- Keep code fences, tables, and embeds valid if they already exist.

## Safety rules

- Do not leave half-broken wikilinks or malformed frontmatter.
- Do not duplicate the same title as both frontmatter and multiple H1 headings.
- Do not turn the final review into a chat transcript or bullet-outline dump.
