---
name: zotero-obsidian-skill-discovery
description: "Search the open skills ecosystem and the web for research skills similar to the user's Zotero/Obsidian workflow needs, then map the best candidates back into Research/Materials outputs."
metadata:
  research_tasks_zh:
    - 文献综述
    - 综述论文
    - 研究报告
    - 数据分析
    - 学术写作
    - 学术演示
  integrations:
    - zotero
    - obsidian
    - web-search
    - skills.sh
    - clawhub.ai
    - github
  output_modes_zh:
    - 本地技能优先
    - 联网发现相似技能
    - 映射回 Obsidian
  obsidian_targets:
    - Research/Materials/Literature Notes
    - Research/Materials/Review Notes
    - Research/Materials/Projects
    - Research/Materials/Figures
    - Research/Materials/Datasets
  zotero_inputs:
    - Better BibTeX JSON
    - citation metadata
    - attachments[].path
    - PDF full text
  discovery_enabled: true
  discovery_priority:
    - local-skills
    - skills-cli
    - skills.sh
    - clawhub.ai
    - github
---

# zotero-obsidian-skill-discovery

Use this skill when the user wants to extend the current Zotero + Obsidian
workflow with similar research skills found online, instead of relying only on
the locally installed stack.

## Goal

Given a research task anchored in Zotero items or Obsidian notes:

1. classify the task using the research workflow map
2. check whether the installed local stack already covers it
3. if coverage is partial or the user explicitly asks for similar skills, search the skills ecosystem and the web
4. map the best candidate back into the existing `Research/Materials/` workflow instead of creating an isolated parallel system

## Local-first routing

Prefer these local skills before searching online:

- `zotero-materials-review` for Better BibTeX JSON -> evidence bundle -> Chinese review draft
- `literature-review` for review methodology, evidence stratification, and research-gap analysis
- `scientific-writing` for turning outlines and evidence into manuscript-grade prose
- `obsidian-markdown` for final Obsidian-safe note structure and links
- `materials-obsidian` for writing notes into `Research/Materials/`
- `deep-research` for deeper evidence gathering and multi-source synthesis when local PDFs and metadata are insufficient

If these cover the request well, use them directly. Search online only when:

- the user explicitly asks to find similar skills
- the task category is not well covered by the installed local stack
- a stronger specialized workflow is likely useful

For the common Zotero -> Chinese review -> Obsidian path, the default local
stack should be:

1. `zotero-materials-review`
2. `literature-review`
3. `scientific-writing`
4. `obsidian-markdown`
5. `materials-obsidian`

## Discovery workflow

### Step 1: Normalize the request

Map the user request to one or more categories from
`references/research-workflow-map.md`.

Use the strongest matching category to derive:

- search keywords
- expected Obsidian output location
- whether Zotero full text is required

### Step 2: Search the ecosystem first

If the `skills` CLI is available, run `skills find <query>` first.

Query style:

- combine the research task with the artifact or workflow
- prefer short keyword pairs like `literature review`, `paper writing`, `manuscript review`, `research proposal`, `presentation slides`, `obsidian`

If the CLI is unavailable or results are weak, search the web using:

- `skills.sh`
- `clawhub.ai`
- GitHub skill repositories

Use `references/discovery-sources.md` for example sources and query patterns.

### Step 3: Evaluate candidates

Prefer candidates that satisfy most of these:

- close match to the research task, not only generic writing help
- explicit academic or evidence-based workflow
- compatible with Markdown or note-based outputs
- adaptable to Zotero metadata, PDFs, or citation workflows

Reject candidates that:

- require a separate proprietary workspace that bypasses Obsidian entirely
- only produce chat answers with no reusable structure
- conflict with the existing `Research/Materials/` directory discipline

### Step 4: Map back into Zotero + Obsidian

Never leave the discovered skill floating as an isolated recommendation.

Always state:

- where the input comes from
  - Zotero JSON
  - Zotero PDF attachments
  - existing Obsidian project note
- which local note path should receive the output
  - `Literature Notes`
  - `Review Notes`
  - `Projects`
  - `Figures`
  - `Datasets`
- whether the discovered skill should be:
  - used as-is
  - adapted into a local skill
  - mined only for workflow ideas

## Output contract

When you respond after discovery, give the user:

1. the matched research task category
2. the best local skill path, if one exists
3. 1-3 discovered external skill candidates
4. the exact way each candidate would plug into Zotero and Obsidian

## Safety rules

- stay within `Research/Materials/` for note outputs
- do not recommend a discovered skill without explaining the Obsidian landing path
- prefer PDF/full-text grounded workflows over metadata-only summaries for serious reviews
- if a discovered skill is useful but not directly compatible, adapt the workflow into local skills rather than abandoning the current system
