# Discovery Sources

Use these sources when searching online for similar skills.

## Priority order

1. local installed skills
2. `skills find <query>` results
3. `skills.sh`
4. `clawhub.ai`
5. GitHub repos that host skill packs

## Verified candidates

These examples were verified on March 29, 2026 with `npx skills find ...` and are good comparison targets for the local Zotero/Obsidian workflow:

- `davila7/claude-code-templates@literature-review`
  - Source: `https://skills.sh/davila7/claude-code-templates/literature-review`
  - Install: `npx skills add https://github.com/davila7/claude-code-templates --skill literature-review`
  - Useful for: systematic reviews, multi-database search, evidence synthesis, verified citations
- `davila7/claude-code-templates@scientific-writing`
  - Source: `https://skills.sh/davila7/claude-code-templates/scientific-writing`
  - Install: `npx skills add https://github.com/davila7/claude-code-templates --skill scientific-writing`
  - Useful for: turning evidence bundles into manuscript-style prose, IMRAD writing, revision passes
- `kepano/obsidian-skills@obsidian-markdown`
  - Source: `https://skills.sh/kepano/obsidian-skills/obsidian-markdown`
  - Install: `npx skills add https://github.com/kepano/obsidian-skills --skill obsidian-markdown`
  - Useful for: Obsidian-flavored Markdown, wikilinks, callouts, frontmatter, embedded PDFs
- `huangwb8/chineseresearchlatex@systematic-literature-review`
  - Source: `https://skills.sh/huangwb8/chineseresearchlatex/systematic-literature-review`
  - Useful for: literature-review workflows with Chinese-academic context
- `collaborative-deep-research/agent-papers-cli@literature-review`
  - Source: `https://skills.sh/collaborative-deep-research/agent-papers-cli/literature-review`
  - Useful for: paper-centric review workflows and evidence aggregation

## Query examples that returned useful results

- `npx skills find "literature review"`
- `npx skills find "scientific writing"`
- `npx skills find obsidian`

Use the first result family that matches the user's actual outcome:

- review-oriented outputs: prefer `literature-review`
- manuscript-oriented outputs: prefer `scientific-writing`
- vault-structure or Markdown outputs: prefer `obsidian-markdown`

## Suggested queries

Use short queries first:

- `literature review`
- `academic researcher`
- `scientific writing`
- `manuscript review`
- `grant proposal`
- `research report`
- `presentation slides`
- `obsidian`

Then add the research domain if needed:

- `materials literature review`
- `chemistry research report`
- `materials presentation slides`
- `scientific manuscript review`

## Adaptation rule

Do not blindly install every discovered skill.

Prefer one of these outcomes:

- install a close-fit skill into the session workspace
- adapt the discovered workflow into a local skill
- keep only the search result as a recommendation and continue with local skills
