# Zotero Review Agent 命令行入口说明

本文档说明当前推荐的本地命令行入口，以及运行后会在 Obsidian 中生成什么。

## 推荐入口

统一使用：

```powershell
python .\ScienceClaw\backend\scripts\run_zotero_review_agent.py `
  --input .\zotero\生成模型.json `
  --topic 生成模型 `
  --vault D:\你的ObsidianVault `
  --overwrite
```

如果不传 `--topic`，默认使用 JSON 文件名去掉扩展名后的 stem。

如果不传 `--category`，默认使用 `topic`。

## 这个入口会做什么

`run_zotero_review_agent.py` 会直接调用 `obsidian_run_zotero_review_agent`，完整执行下面这条链路：

1. 校验 Better BibTeX JSON
2. 构建 review bundle 和本地证据文件
3. 导入或更新 literature notes
4. 生成 review 草稿
5. 进行最终润色
6. 写回同一份 Obsidian review note

## 典型输出

在 Obsidian vault 中会写入：

```text
Research/Materials/
  Templates/
    literature-note.md
    review-note.md
  Literature Notes/
    <category>/
      <paper>.md
  Review Notes/
    <category>/
      <topic> - review.md
```

同时，返回结果里还会包含：

- `review_bundle_path`
- `review_input_path`
- `review_draft_path`
- `effective_vault_dir`
- `vault_match_status`

## 模型配置

如果你需要在命令行里显式指定最终润色使用的模型配置，可以二选一：

```powershell
--model-config-json "{...}"
```

或

```powershell
--model-config-file .\path\to\model-config.json
```

如果两者都不传，CLI 会回退到工具默认的环境变量或配置源。

当默认模型配置不可用或鉴权失败时，整条链路仍会完成，但最终 review 会退回结构化 draft，而不是经过 LLM 润色后的版本。

## 关于旧入口

旧的 `import_zotero_bbt_to_obsidian.py` CLI 包装器已经移除。

原因是它只覆盖 import-only 流程，容易让命令行入口与实际推荐工作流分叉。现在统一以 `run_zotero_review_agent.py` 作为推荐入口。

如果你只想做导入、不想走最终综述链路，仍然可以直接调用底层工具 `obsidian_import_zotero_bbt_json`，但不再单独提供一个 import-only CLI 包装脚本。
