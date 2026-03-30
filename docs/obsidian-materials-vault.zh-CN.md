# 现有 Obsidian Vault 复用说明

本文档说明如何让 ScienceClaw 将材料科研笔记直接写入你现有的 Obsidian vault，而不是新建独立项目或独立知识库。

## 目标

- 复用现有 Obsidian vault
- 将 AI for Materials 相关产物固定写入 `Research/Materials/`
- 保留 Zotero / Better BibTeX 兼容字段，便于后续引用插件接管

## 容器挂载

默认容器内路径固定为：

```text
/home/scienceclaw/obsidian_vault
```

宿主机路径通过环境变量控制：

```text
OBSIDIAN_VAULT_HOST_PATH
```

如果不设置，默认回退到仓库内的：

```text
./workspace/obsidian_vault
```

### Windows 建议写法

在 `.env` 或 shell 环境中优先使用正斜杠路径，例如：

```text
OBSIDIAN_VAULT_HOST_PATH=D:/Obsidian/MyVault
```

## 目录规范

ScienceClaw 只会在以下子树中创建或更新内容：

```text
Research/Materials/Literature Notes/
Research/Materials/Review Notes/
Research/Materials/Projects/
Research/Materials/Figures/
Research/Materials/Datasets/
Research/Materials/Templates/
```

## 可复用工具

新增工具：

```text
obsidian_write_materials_note
```

功能：

- 初始化 `Research/Materials/` 目录结构
- 写入文献卡片
- 写入综述笔记
- 写入项目笔记
- 自动保留 `doi`、`citekey`、`zotero_key`

## 文件命名规则

### 文献卡片

优先：

```text
<citekey> - <short title>.md
```

### 综述笔记

优先：

```text
<topic> - review.md
```

### 项目笔记

位于：

```text
Research/Materials/Projects/<topic>/
```

## Zotero 联动边界

当前实现不做 Zotero 写回，仅做字段兼容：

- `doi`
- `citekey`
- `zotero_key`

如果你已经使用 Obsidian 的 Zotero Integration 或引用插件，生成的文献卡片可以直接被后续插件流程接管。

## 默认模板

首次调用工具时会自动在：

```text
Research/Materials/Templates/
```

中生成三类模板：

- `Literature Note Template.md`
- `Review Note Template.md`
- `Project Note Template.md`

## 建议工作流

1. 在 Docker 环境中挂载你现有的 vault
2. 调用 `obsidian_write_materials_note` 完成 Materials 区域初始化
3. 用同一工具持续写入文献卡片、综述和项目笔记
4. 将图件与数据文件统一放在 `Figures/` 与 `Datasets/`

这样可以保证：

- 不污染你现有的 Obsidian 其他区域
- Zotero 信息可追溯
- ScienceClaw 生成的结果可直接在 Obsidian 中浏览和管理
