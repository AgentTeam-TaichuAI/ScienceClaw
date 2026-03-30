# Zotero JSON 到 Obsidian 中文综述测试说明

本文档说明如何验证新的两阶段链路：

1. 导入 Zotero / Better BibTeX JSON，生成 literature notes
2. 构建 review bundle，提取 PDF / HTML 证据，支持中文综述写作

## 适用场景

- 已经有 Better BibTeX 自动导出的 JSON
- 本地 Zotero 附件可访问，或可通过 host bridge 读取
- 希望把结果写入现有 Obsidian vault 的 `Research/Materials/`

## 核心工具

- `obsidian_import_zotero_bbt_json`
- `obsidian_build_zotero_review_bundle`
- `obsidian_write_materials_note`

## 推荐流程

### 1. 只导入 literature notes

```powershell
python .\ScienceClaw\backend\scripts\import_zotero_bbt_to_obsidian.py `
  --input .\zotero\生成模型.json `
  --topic 生成模型 `
  --vault D:\你的ObsidianVault `
  --no-review
```

### 2. 构建 review bundle

在工具链或 Python 调用中执行：

- `export_json_path=...\zotero\生成模型.json`
- `language="zh"`
- `prefer_pdf_fulltext=true`
- `relevance_policy="balanced"`

生成结果：

- `research_data/review_bundle.json`
- `research_data/paper_evidence/*.json`
- `research_data/attachments_cache/*`（仅在需要 host bridge 拉回附件时出现）

### 3. 写入中文综述

使用：

- `note_type="review"`
- `review_style="survey_cn"`
- `filename_style="title"`
- `conflict_mode="timestamp"`

这样会生成类似：

- `Research/Materials/Review Notes/生成模型在材料设计与发现中的应用综述.md`

如已存在同名文件，则自动生成：

- `Research/Materials/Review Notes/生成模型在材料设计与发现中的应用综述（YYYYMMDD-HHmmss）.md`

## 推荐检查点

- 能识别 `生成模型.json` 中的 14 篇 parent items
- `review_bundle.json` 中包含 `suggested_title`
- `metadata_conflicts` 会标出错配摘要条目
- `core_papers / boundary_papers / noise_papers` 分层合理
- architecture / PEFT 这类论文不进入核心主线
- 综述标题和一级章节为简体中文

## 当前边界

- bundle 负责证据整理，不直接替你写完整综述正文
- 最终综述质量仍取决于后续 deep-research 写作阶段
- 如果 PDF 无法读取，会退回 HTML / TXT / JSON 摘要，并在 bundle 中记录原因
