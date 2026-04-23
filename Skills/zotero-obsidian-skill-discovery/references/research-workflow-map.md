# Research Workflow Map

Use this map to translate the user's request into:

- a research task category
- a skill discovery query
- a Zotero input expectation
- an Obsidian output target

| 科研任务 | Recommended discovery queries | Zotero anchor | Preferred Obsidian target | Local-first fallback |
|---|---|---|---|---|
| 文献综述 | `literature review`, `academic researcher`, `research synthesis` | Better BibTeX JSON + PDF | `Research/Materials/Review Notes/` | `zotero-materials-review` |
| 综述论文 | `paper writing`, `scientific writing`, `academic paper writer` | JSON + core paper set | `Research/Materials/Review Notes/` | `zotero-materials-review` + `materials-obsidian` |
| 思辨论文 | `research argument`, `position paper`, `critical review` | curated literature notes | `Research/Materials/Projects/` | `deep-research` |
| 方法论文 | `method paper`, `technical writing`, `research methods` | method-centric paper set | `Research/Materials/Projects/` | `deep-research` |
| 实验方案 | `experiment design`, `study design`, `research protocol` | literature notes + project assumptions | `Research/Materials/Projects/` | `deep-research` |
| 基金课题 | `research proposal`, `grant proposal`, `academic proposal` | prior notes + review bundle | `Research/Materials/Projects/` | `deep-research` |
| 研究报告 | `research report`, `technical report`, `scientific writing` | review bundle + evidence JSON | `Research/Materials/Projects/` | `deep-research` |
| 创新专利 | `patent drafting`, `invention disclosure`, `technical patent` | project note + prior art set | `Research/Materials/Projects/` | `deep-research` |
| 数据分析 | `research analysis`, `statistical analysis`, `data science` | extracted tables / datasets | `Research/Materials/Datasets/` + `Projects/` | `deep-research` |
| 数据可视化 | `data visualization`, `research figures`, `scientific charts` | cleaned datasets | `Research/Materials/Figures/` | `materials-obsidian` |
| 学术海报 | `academic poster`, `research poster`, `conference poster` | project summary + figures | `Research/Materials/Projects/` | `materials-obsidian` |
| 学术PPT | `presentation slides`, `research presentation`, `ppt` | project summary + figures | `Research/Materials/Projects/` | `materials-obsidian` |
| 同行审校 | `manuscript review`, `scholar evaluation`, `peer review` | draft note or manuscript | `Research/Materials/Projects/` | `deep-research` |

## Routing guidance

- If the user starts from Zotero data, prefer workflows that can ingest references and full text.
- If the user starts from an existing Obsidian note, prefer skills that improve structure, argument, or presentation while keeping Markdown outputs.
- If the task needs a final note rather than a chat answer, always choose the Obsidian target before recommending the skill.
