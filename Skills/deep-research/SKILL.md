---
name: deep-research
description: "多源深度调研与专业报告生成。适用场景广泛——只要用户的问题涉及需要深度分析的专业话题，就应使用此技能。包括但不限于：(1) 用户明确要求调研/research/综述/报告/发现；(2) 用户提出一个技术或科学话题，话题复杂度需要多源深度分析；(3) 用户要求对比多种技术方案的优劣；(4) 涉及生物医药、蛋白质、基因、药物靶点等需要专业数据库支撑的问题。核心能力：根据问题性质自动组合 arXiv 论文检索 + ToolUniverse 科学工具（UniProt/OpenTargets/PubMed/FAERS 等 1000+ 工具）+ Web 搜索，多源采集数据，交叉分析，生成专业 PDF/DOCX 研究报告。"
---

# Deep Research — 多源深度调研系统

端到端的深度调研系统：从用户问题出发，智能选择数据源组合（arXiv 论文 + ToolUniverse 科学工具 + Web 搜索），多维度采集数据，逐源深度解读，围绕用户问题进行交叉归纳，最终生成专业研究报告。

## 工作流程总览

```
Phase 1: 问题拆解与数据源规划
→ Phase 2: 多源数据采集
    2A: arXiv 论文检索 + 筛选 + PDF 下载
    2B: ToolUniverse 科学工具数据采集
    2C: Web 搜索补充采集
→ Phase 3: 数据提取与整理
→ Phase 4: 逐源深度解读
→ Phase 5: 围绕用户问题的交叉分析与报告撰写
→ Phase 6: 生成 PDF/DOCX 研究报告
```

**工作空间路径**：所有文件输出到 `/home/scienceclaw/sessionid/` 目录下。

---

## Phase 1: 问题拆解与数据源规划

收到用户问题后，**不要直接执行**。先分析问题，拆解为多个调研维度，并规划需要哪些数据源。

### 1.1 问题拆解

将用户问题按以下维度展开：

| 维度 | 说明 | 示例 |
|------|------|------|
| 核心概念 | 问题的主题词 | BRCA1, data center cooling |
| 技术路线 | 不同的技术方案 | PARP inhibitors, liquid cooling |
| 应用场景 | 特定的应用环境 | triple-negative breast cancer |
| 关联领域 | 密切相关的交叉领域 | DNA repair, homologous recombination |
| 优化目标 | 关注的性能指标 | survival rate, PUE |

### 1.2 数据源决策

**⚠️ 强制规则：对于任何研究型问题，ToolUniverse 和文献检索都是必选项，不可跳过。**

| 数据源 | 状态 | 说明 | 典型场景 |
|--------|------|------|----------|
| **文献检索** | **必选** | 任何研究问题都必须检索学术文献。根据领域选择来源：CS/AI/物理/数学 → arXiv；生物医药/化学 → PubMed/PubTator/EuropePMC（通过 ToolUniverse）；通用学术 → OpenAlex/Semantic Scholar（通过 ToolUniverse）。**多个来源可叠加使用。** | 所有研究型问题 |
| **ToolUniverse** | **必选** | 任何研究问题都必须使用 ToolUniverse 获取专业数据库的结构化数据。即使不涉及生物医药，也应搜索是否有适用工具（天文、地球科学、化学、统计等均有覆盖）。 | 所有研究型问题 |
| **Web 搜索** | 推荐 | 获取最新资讯、行业报告、非学术数据补充 | 市场规模、最新进展、政策法规 |

**决策原则**：
- **文献检索 + ToolUniverse 是所有研究任务的双必选底线**，Web 搜索作为推荐补充
- 生物医药领域：ToolUniverse（UniProt/OpenTargets/PubMed/PubTator 等结构化数据） + 文献检索（`PubTator_search_publications` 或 `EuropePMC_search` 通过 ToolUniverse 调用，以及 arXiv 补充前沿预印本） + Web 搜索
- CS/AI/工程领域：arXiv 论文检索 + ToolUniverse（搜索领域相关工具如 HuggingFace/OpenML/DBLP 等） + Web 搜索
- 跨学科/其他领域：arXiv（如适用） + ToolUniverse（搜索领域工具，如天文 SIMBAD/NASA、地球科学 USGS、化学 COD 等） + 通用文献检索（OpenAlex/Semantic Scholar 通过 ToolUniverse） + Web 搜索
- **绝对禁止**只用单一数据源就直接开始写报告

### 1.3 生成调研计划

将上述分析写入计划文件：

```python
import json

plan = {
    "question": "用户原始问题",
    "dimensions": ["维度1", "维度2", "..."],
    "data_sources": {
        "literature": {
            "enabled": True,  # ⚠️ 必选 — 不可设为 False
            "arxiv": {
                "enabled": True,  # CS/AI/物理/数学/工程领域必须启用
                "queries": [
                    {"arxiv_query": "abs:%22keyword%22+AND+abs:topic", "label": "描述"},
                    # ... 8-12 个 query
                ],
                "relevance_phrases": ["phrase1", "phrase2"],
                "target_total": 50,
                "top_k": 15,
            },
            "pubmed_via_tooluniverse": {
                "enabled": True,  # 生物医药/健康领域必须启用
                "tools": ["PubTator_search_publications", "EuropePMC_search"],
                "queries": ["搜索词1", "搜索词2"],
            },
            "general_academic": {
                "enabled": True,  # 通用学术文献检索
                "tools": ["OpenAlex_search_works", "SemanticScholar_search_papers"],
                "queries": ["搜索词1", "搜索词2"],
            },
        },
        "tooluniverse": {
            "enabled": True,  # ⚠️ 必选 — 不可设为 False
            "tasks": [
                {"tool_query": "protein function", "purpose": "获取蛋白功能信息", "example_tool": "UniProt_get_function_by_accession"},
                {"tool_query": "disease targets", "purpose": "获取疾病靶点", "example_tool": "OpenTargets_get_associated_targets_by_disease_efoId"},
                # ... 根据需求列出 3-8 个 ToolUniverse 任务
            ],
        },
        "web_search": {
            "enabled": True,  # 推荐启用
            "queries": ["搜索词1", "搜索词2"],
        },
    },
    "output_dir": "/home/scienceclaw/sessionid",
}

with open("/home/scienceclaw/sessionid/research_plan.json", "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)
```

---

## Phase 2: 多源数据采集

根据 Phase 1 的计划，并行或顺序执行各数据源的采集。所有采集结果保存到 `research_data/` 目录。

**⚠️ 强制检查点：Phase 2 必须同时包含"文献检索"和"ToolUniverse 数据采集"两个环节。如果你发现自己只做了其中一个就准备进入 Phase 3，请停下来补齐另一个。**

### 2A: arXiv 论文检索（如已启用）

#### 构造 arXiv API Query

每个 query 使用 arXiv API 的搜索语法：

**基本规则**：
- `abs:` 搜索摘要字段（最常用）
- `ti:` 搜索标题字段
- `+AND+` 连接多个条件（交集）
- `+OR+` 连接多个条件（并集）
- `%22` 用于包裹精确短语（URL 编码的双引号）
- 单词间用 `+` 连接

**Query 构造示例**：

```
abs:%22data+center%22+AND+abs:cooling
abs:%22liquid+cooling%22+AND+abs:%22data+center%22
abs:%22immersion+cooling%22
ti:%22exact+phrase%22+AND+abs:keyword
cat:cs.AI+AND+abs:%22large+language+model%22
```

#### 生成 search_config.json 并执行

```python
import json

config = {
    "question": "用户原始问题",
    "queries": [
        {"arxiv_query": "abs:%22keyword%22+AND+abs:topic", "label": "描述"},
        # ... 8-12 个 query
    ],
    "target_total": 50,
    "top_k": 15,
    "output_dir": "/home/scienceclaw/sessionid/research_papers",
    "relevance_phrases": ["phrase1", "phrase2"],
    "min_score": 4
}

with open("/home/scienceclaw/sessionid/search_config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
```

```bash
python3 /skills/deep-research/scripts/arxiv_paper_finder.py /home/scienceclaw/sessionid/search_config.json
```

**脚本工作流程**：多 Query 搜索 → 去重 → 相关性评分 → 筛选 TOP-K → 下载 PDF

**评分规则**：标题命中 +5 分/短语，摘要命中 +2 分/短语，多 query 命中 +3 分/额外命中，2025年+ +3分，2024年 +2分，2023年 +1分。

**执行后检查**：确认 `all_candidates.json`（40-60 篇）、`selected_papers.json` 质量、PDF 文件完整性。

### 2B: ToolUniverse 数据采集（⚠️ 必选）

使用 `tooluniverse_search` → `tooluniverse_info` → `tooluniverse_run` 三步流程采集专业数据。

**此步骤包含两个必须完成的子任务：**
1. **专业数据库采集**：获取领域特定的结构化数据
2. **学术文献检索**：通过 ToolUniverse 中的文献检索工具获取相关论文（此步骤**必须执行**，与 2A 的 arXiv 互补）

**工作流程**：

1. **搜索工具**：对每个任务维度，用 `tooluniverse_search` 找到合适的工具
2. **查看规格**：用 `tooluniverse_info` 确认参数要求
3. **执行采集**：用 `tooluniverse_run` 获取数据
4. **保存结果**：将每次调用结果保存到 `research_data/` 目录

```
# ── 子任务 1: 专业数据库采集 ──

# 示例：蛋白功能调研
tooluniverse_search(query="protein function analysis", limit=5)
tooluniverse_info(tool_name="UniProt_get_function_by_accession")
tooluniverse_run(tool_name="UniProt_get_function_by_accession", arguments='{"accession": "P38398"}')
→ write_file("research_data/uniprot_P38398_function.json", result)

# 示例：疾病靶点
tooluniverse_search(query="disease drug targets", limit=5)
tooluniverse_run(tool_name="OpenTargets_get_associated_targets_by_disease_efoId", arguments='{"efoId": "EFO_0000305"}')
→ write_file("research_data/opentargets_breast_cancer_targets.json", result)

# ── 子任务 2: 学术文献检索（⚠️ 必须执行） ──
# 无论什么领域，都必须执行以下至少一种文献检索：

# 生物医药领域 → PubMed/PubTator
tooluniverse_run(tool_name="PubTator_search_publications", arguments='{"query": "BRCA1 mutation breast cancer", "limit": 20}')
→ write_file("research_data/pubmed_brca1_publications.json", result)

# 生物医药领域 → EuropePMC
tooluniverse_run(tool_name="EuropePMC_search", arguments='{"query": "BRCA1 PARP inhibitor", "limit": 20}')
→ write_file("research_data/europepmc_brca1_parp.json", result)

# 通用学术 → OpenAlex（覆盖所有学科）
tooluniverse_search(query="academic paper search", limit=5)
tooluniverse_run(tool_name="OpenAlex_search_works", arguments='{"query": "topic keywords", "limit": 20}')
→ write_file("research_data/openalex_results.json", result)

# CS/AI 领域 → DBLP
tooluniverse_run(tool_name="DBLP_search_publications", arguments='{"query": "large language model", "limit": 20}')
→ write_file("research_data/dblp_results.json", result)
```

**常用 ToolUniverse 工具类别**：

| 类别 | 典型工具 | 用途 |
|------|----------|------|
| ⚠️ **文献检索（必选）** | `PubTator_search_publications`, `EuropePMC_search`, `OpenAlex_search_works`, `SemanticScholar_search_papers`, `DBLP_search_publications` | **每次调研都必须检索学术文献** |
| 蛋白分析 | `UniProt_get_entry_by_accession`, `UniProt_get_function_by_accession` | 蛋白结构、功能、修饰位点 |
| 疾病靶点 | `OpenTargets_get_associated_targets_by_disease_efoId` | 疾病相关靶点排名 |
| 药物安全 | `FAERS_count_reactions_by_drug_event` | 不良反应统计 |
| 基因变异 | `ClinVar_*`, `GWAS_*` | 临床变异、GWAS 关联 |
| ADMET | `ADMETAI_predict_*` | 药物动力学预测 |
| 分子对接 | `boltz2_docking` | 蛋白-配体对接 |
| 天文学 | `Simbad_*`, `SDSS_*`, `NASAExoplanet_*` | 天体数据、巡天数据 |
| 地球科学 | `USGS_*`, `ERDDAP_*`, `SoilGrids_*` | 地震、水文、海洋气候 |
| 化学材料 | `COD_*` | 晶体结构 |
| 社会统计 | `WorldBank_*`, `Eurostat_*` | 经济社会指标 |

**关键原则**：
- 每个 ToolUniverse 调用结果都 `write_file` 保存到 `research_data/` 目录
- 大型结果先保存原始 JSON，再写一个清洁版的摘要文件
- 对未知工具名称，先 `tooluniverse_search` 发现，再 `tooluniverse_info` 确认参数

### 2C: Web 搜索补充采集（如已启用）

使用 `web_search` + `web_crawl` 获取非学术来源的补充数据：

```
web_search("BRCA1 PARP inhibitor clinical trials 2024")
→ write_file("research_data/web_parp_trials.md", result)

web_crawl("https://specific-url.com/report")
→ write_file("research_data/web_industry_report.md", result)
```

---

## Phase 3: 数据提取与整理

### 3.1 论文文本提取（如有 arXiv 论文）

对每篇已下载的 PDF 提取全文。优先用 `pdftotext -layout`，不可用时回退 PyMuPDF。

```bash
# 检查工具可用性
which pdftotext && echo "pdftotext OK" || echo "pdftotext NOT FOUND"
python3 -c "import fitz; print('PyMuPDF OK')" 2>/dev/null || python3 -m pip install --user pymupdf
```

**方案 A（首选）—— pdftotext**：

```bash
cd /home/scienceclaw/sessionid/research_papers
for pdf in *.pdf; do
    txt="${pdf%.pdf}.txt"
    if [ ! -f "$txt" ]; then
        pdftotext -layout "$pdf" "$txt"
        echo "Extracted: $pdf -> $txt"
    fi
done
```

**方案 B（回退）—— PyMuPDF**：

```python
import fitz, os, glob

pdf_dir = "/home/scienceclaw/sessionid/research_papers"
for pdf_path in sorted(glob.glob(os.path.join(pdf_dir, "*.pdf"))):
    txt_path = pdf_path.replace(".pdf", ".txt")
    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
        continue
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text", sort=True)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[OK] {os.path.basename(pdf_path)} -> {os.path.basename(txt_path)} ({len(text)} chars)")
    doc.close()
```

### 3.2 ToolUniverse 数据整理

读取 `research_data/` 下的所有 JSON/MD 文件，用 `read_file` 逐个检查数据质量，提取关键信息写入摘要文件：

```
write_file("research_data/data_summary.md", """
## 采集数据概览
- UniProt P38398: BRCA1 蛋白功能数据 ✓（含 RING/BRCT 结构域信息）
- OpenTargets EFO_0000305: 乳腺癌靶点排名 ✓（Top 20 靶点）
- PubTator 文献: 20 篇相关论文摘要 ✓
- Web 搜索: 最新临床试验数据 ✓
- arXiv: 15 篇精选论文 ✓
""")
```

---

## Phase 4: 逐源深度解读

### 4.1 论文深度解读（如有）

对每篇论文进行结构化深度解读，采用两轮阅读策略：

**第一轮（快速扫描）**：从 `selected_papers.json` 读取 abstract，建立初步印象。

**第二轮（深度阅读）**：用 `read_file` 的 offset/limit 参数按段读取 `.txt` 文件，重点关注 Introduction（前 100-150 行）和 Results/Conclusion（后 1/3 部分）。

为每篇论文写入结构化摘要：

```
write_file("paper_summaries/summary_{paper_id}.txt", """
【论文标题】{英文原标题}
【arXiv ID】{paper_id}
【作者】{前3位作者}, et al.
【发表日期】{年-月-日}

【研究问题】
该论文要解决什么问题？1-2 句话。

【核心方法】
提出了什么技术方案/方法？关键创新点是什么？3-5 句话。

【关键发现/实验结果】
- 具体数据点 1（必须包含量化数据）
- 具体数据点 2
- 具体数据点 3

【与用户问题的关联】
这篇论文回答了用户问题的哪个方面？1-2 句话。

【局限性与未来方向】
1-2 句话。
""")
```

### 4.2 ToolUniverse 数据解读

对每个 ToolUniverse 采集的数据文件，`read_file` 并提取关键发现，写入摘要：

```
write_file("data_summaries/summary_uniprot_brca1.txt", """
【数据来源】UniProt P38398 (BRCA1_HUMAN)
【关键发现】
- BRCA1 蛋白含 1863 个氨基酸，包含 RING 结构域（1-109）和 BRCT 结构域（1646-1859）
- 参与同源重组修复（HR）、细胞周期 G2/M 检查点调控
- 已知致病突变 > 1800 个，185delAG 和 5382insC 为 founder mutations
【与用户问题的关联】
直接回答了 BRCA1 蛋白功能机制部分的需求。
""")
```

### 4.3 Web 数据解读

对 Web 搜索结果同样提取关键信息，写入摘要文件。

---

## Phase 5: 围绕用户问题的交叉分析与报告撰写

**此阶段是从「逐源阅读」到「综合洞察」的质变。** 不再逐源叙述，而是以用户的原始问题为轴心，跨数据源提取、对比、归纳。

### 5.1 确定报告章节

阅读完所有 Phase 4 摘要后，动态决定章节结构（选择 4-7 个最适合用户问题的维度）：

| 分析维度 | 适用条件 | 文件名示例 |
|----------|----------|------------|
| 研究背景与意义 | 所有调研 | `sec_01_background.txt` |
| 技术路线/方法分类与对比 | 多种方案可比较 | `sec_02_methods.txt` |
| 关键数据与实验发现 | 有量化数据 | `sec_03_findings.txt` |
| 蛋白/基因功能机制 | 涉及分子生物学 | `sec_04_mechanism.txt` |
| 靶向治疗/药物进展 | 涉及药物研发 | `sec_05_therapeutics.txt` |
| 应用场景分析 | 有明确场景差异 | `sec_06_applications.txt` |
| 挑战与展望 | 多源指出共同问题 | `sec_07_challenges.txt` |

### 5.2 撰写各章节

每个章节写入独立文件，每个章节 **不少于 1500 字**：

```
write_file("sections/sec_01_background.txt", content)
write_file("sections/sec_02_methods.txt", content)
...
```

**写作风格 — 学术研究报告（CRITICAL）：**

- **连续流畅的散文段落**。每段 8-10 句，遵循：主题句 → 具体数据支撑的证据 → 分析/对比 → 过渡到下一个论点。
- **跨来源综合**：将论文数据、ToolUniverse 数据、Web 数据交织在一起叙述。例如："UniProt 数据显示 BRCA1 蛋白的 RING 结构域（残基 1-109）具有 E3 泛素连接酶活性 [1]，而 Zhang 等人的研究进一步表明该结构域的 C61G 突变会完全消除其泛素化功能 [2]，OpenTargets 平台的靶点关联分析将 BRCA1 列为乳腺癌排名第 3 的治疗靶点，这一排名与近年 PARP 抑制剂临床试验的成功密切相关 [3]。"
- **行内引用** `[1]`, `[2]`，引用编号对应最终参考文献列表。不要在每章末尾加"参考文献"列表——所有引用统一放在报告最后的 `references` section。
- **学术连接词**："Furthermore"、"In contrast"、"These findings indicate"、"Notably"、"Taken together"、"此外"、"与之对比"、"上述结果表明"。
- **绝对禁止**编号要点结构（如 "1. 标题\n\n段落. 2. 标题\n\n段落."）。使用 `##` 子标题作为结构，散文段落作为内容。
- **要点列表不超过 5%**，仅用于简短枚举（如 4-5 个药物名称）。
- **必须包含具体数据**：数字、百分比、p 值、置信区间、对比结果。

**⚠️ 语言要求（CRITICAL）：**
- 所有报告内容（标题、副标题、章节标题、正文、图表标签、封面信息）必须使用**用户在系统提示词 `## Language` 中配置的语言**。
- 用户语言为中文（`zh`）时，整篇报告用中文撰写；用户语言为英文（`en`）时，整篇报告用英文撰写。
- 除专有名词或无标准翻译的技术术语外，不要混用语言。

### 5.3 撰写执行摘要和结论

```
write_file("sections/executive_summary.txt", ...)
write_file("sections/conclusion.txt", ...)
```

**执行摘要**（400-600 字散文段落）：用户问题的核心回答 + 最重要的 3-5 个发现 + 建议。

**结论与展望**（600-1000 字散文段落）：综合各来源的关键结论 + 技术/领域成熟度评估 + 最有前景的方向 + 尚待解决的关键问题。

### 5.4 验证

```
python3 -c "import os,glob; [print(f'{f}: {len(open(f).read())} chars') for f in sorted(glob.glob('sections/*.txt'))]; total=sum(len(open(f).read()) for f in glob.glob('sections/*.txt')); print(f'TOTAL: {total} chars, ~{total//500} pages')"
```

如果总字数不足目标，做 **一次修订**：`read_file` 数据再看一遍，然后 `write_file` 重写最薄的 1-2 个章节。不要循环修订。

---

## Phase 6: 生成研究报告

使用 pdf 或 docx skill 的模板生成专业报告。**默认生成 PDF，用户要求 Word 时生成 DOCX。**

### 6.1 复制报告生成器

```bash
# PDF 报告
cp /builtin-skills/pdf/scripts/generate_report.py /home/scienceclaw/sessionid/generate_report.py

# 或 DOCX 报告
cp /builtin-skills/docx/scripts/generate_report.js /home/scienceclaw/sessionid/generate_report.js
```

**Preferred fallback path**: if the workspace already has `sections/*.txt`, do not hand-write another `report_data.json` assembler on the fly. Copy and run `/skills/deep-research/scripts/build_report_data.py` instead; it prefers `research_plan.json` / `research_data/all_references.json` when available, but can also fall back to the existing section files and optionally generate the PDF directly.

```bash
cp /skills/deep-research/scripts/build_report_data.py /home/scienceclaw/sessionid/build_report_data.py
python3 /home/scienceclaw/sessionid/build_report_data.py \
  --base-dir /home/scienceclaw/sessionid \
  --title "Report Title" \
  --pdf-output /home/scienceclaw/sessionid/final_report.pdf
```

**Completion rule**: if the user asked for a PDF, the task is not complete until `final_report.pdf` actually exists. Copying `generate_report.py` or only writing `sections/*.txt` does not count as delivery.

**关键**：必须用 shell `cp` 复制，不要自己写报告生成代码。

### 6.2 组装 report_data.json

编写 Python 脚本，将 sections 目录下的各章节文件 + 参考文献组装为 `report_data.json`：

```python
import json, glob, os

BASE = "/home/scienceclaw/sessionid"
SECTIONS_DIR = f"{BASE}/sections"

# ── 构建参考文献列表（⚠️ CRITICAL：必须覆盖所有数据源） ──
# 正文中每个 [n] 引用标记都必须在此列表中有对应条目，
# 否则 PDF 生成时会因锚点缺失而崩溃。
references = []

# 来源 1: arXiv 论文（如有）
papers_file = f"{BASE}/research_papers/selected_papers.json"
if os.path.exists(papers_file):
    selected = json.load(open(papers_file, encoding="utf-8"))
    for p in selected:
        authors = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors += " et al."
        references.append(f'{authors}. {p["title"]}. arXiv:{p["id"]}, {p["published"]}. https://arxiv.org/abs/{p["id"]}')

# 来源 2: ToolUniverse 数据源（必须为每个使用的工具添加引用）
# 示例：references.append("UniProt Consortium. UniProt: the Universal Protein Knowledgebase. Nucleic Acids Res, 2025. https://www.uniprot.org/")
# 示例：references.append("Ochoa D, et al. Open Targets Platform. Nucleic Acids Res, 2023. https://platform.opentargets.org/")

# 来源 3: Web 搜索来源（必须为引用的网页/报告添加引用）
# 示例：references.append("WHO. Breast Cancer Fact Sheet. 2024. https://www.who.int/news-room/fact-sheets/detail/breast-cancer")

# 来源 4: PubMed/EuropePMC 文献（通过 ToolUniverse 检索的论文）
# 示例：references.append("Smith J, et al. Title of paper. Journal Name, 2024. https://doi.org/10.xxxx/xxxxx")

# ── 章节配置（根据实际内容调整） ──
SECTION_MAP = [
    ("executive_summary.txt", "1.", "执行摘要", None),
    ("sec_01_*.txt", "2.", "研究背景与意义", None),
    ("sec_02_*.txt", "3.", "方法与技术路线", {
        "type": "chart_pie",
        "title": "研究方法分布",
        "labels": ["方法A", "方法B", "方法C", "其他"],
        "values": [35, 30, 20, 15]
    }),
    ("sec_03_*.txt", "4.", "关键发现与数据分析", {
        "type": "chart_bar",
        "title": "关键指标对比",
        "categories": ["指标1", "指标2", "指标3"],
        "series": [{"name": "数值", "values": [85, 72, 91]}]
    }),
    ("sec_04_*.txt", "5.", "机制/原理深度解析", None),
    ("sec_05_*.txt", "6.", "应用与治疗进展", {
        "type": "chart_line",
        "title": "趋势分析",
        "x_labels": ["2020", "2021", "2022", "2023", "2024"],
        "series": [{"name": "指标", "values": [40, 55, 62, 70, 78]}]
    }),
    ("sec_06_*.txt", "7.", "挑战与展望", None),
    ("conclusion.txt", "8.", "结论", None),
]

data = {
    "title": "根据用户问题生成的报告标题",
    "subtitle": "深度调研报告",
    "short_title": "调研报告",
    "report_type": "深度调研报告",
    "toc": True,
    # CRITICAL: Do NOT include page count or total pages in cover_meta —
    # the page count is unknown at assembly time and produces inaccurate information.
    "cover_meta": [
        ["报告类型", "多源深度调研报告"],
        ["生成日期", "YYYY-MM-DD"],
        ["数据来源", "arXiv / ToolUniverse / Web"],
        ["研究问题", "用户原始问题"],
    ],
    "disclaimer": "本报告由 AI 基于多源数据自动生成，包括学术论文、专业数据库和公开资料。请结合实际情况参考使用。",
    "sections": [],
}

for pattern, num, heading, chart in SECTION_MAP:
    matches = sorted(glob.glob(os.path.join(SECTIONS_DIR, pattern)))
    if not matches:
        continue
    body = open(matches[0], encoding="utf-8").read().strip()
    data["sections"].append({"type": "heading", "level": 1, "number": num, "text": heading})
    data["sections"].append({"type": "text", "body": body})
    if chart:
        data["sections"].append(chart)

# 参考文献
data["sections"].append({"type": "heading", "level": 1, "number": f"{len([s for s in SECTION_MAP if glob.glob(os.path.join(SECTIONS_DIR, s[0]))])+1}.", "text": "参考文献"})
data["sections"].append({"type": "references", "items": references})

with open(f"{BASE}/report_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Generated report_data.json ({len(data['sections'])} section blocks)")
```

**注意**：
- 根据实际分析内容调整 `SECTION_MAP`，可增减章节
- 图表数据必须来自实际采集的数据，不要编造
- chart 类型：`chart_pie`（分布）、`chart_bar`（对比）、`chart_line`（趋势）
- 也可以在 text body 中嵌入 Markdown 表格（`| col1 | col2 |`），模板会自动渲染

**⚠️ 图表维度约束（CRITICAL — 不遵守会导致 PDF 生成崩溃）：**
- `chart_bar`：`categories` 数组长度必须 == 每个 `series[i].values` 数组长度。例如 3 个 categories 则每个 series 必须恰好 3 个 values
- `chart_pie`：`labels` 数组长度必须 == `values` 数组长度
- `chart_line`：`x_labels` 数组长度必须 == 每个 `series[i].values` 数组长度
- 构造图表数据后，**必须人工核查数组长度一致**再写入 SECTION_MAP

**⚠️ 引用一致性约束（CRITICAL — 不遵守会导致 PDF 生成崩溃）：**
- 正文 `[n]` 标记中的最大数字 n **不得超过** `references` 列表的条目数。例如正文用了 `[1]` 到 `[15]`，则 `references` 列表必须至少有 15 条
- 如果 `references` 为空（0 条），则正文中**禁止使用**任何 `[n]` 引用标记
- 组装完成后运行下方校验脚本检查一致性

### 6.3 生成最终报告

```bash
cd /home/scienceclaw/sessionid

# PDF 报告
python3 generate_report.py report_data.json final_report.pdf

# 或 DOCX 报告
node generate_report.js report_data.json final_report.docx
```

### 6.4 质量校验

```bash
python3 -c "
import json, re
data = json.load(open('/home/scienceclaw/sessionid/report_data.json'))
total = sum(len(s.get('body', '')) for s in data['sections'])
secs = sum(1 for s in data['sections'] if s['type'] == 'heading')
refs = sum(len(s.get('items', [])) for s in data['sections'] if s['type'] == 'references')
print(f'总字数: {total}')
print(f'章节数: {secs}')
print(f'参考文献: {refs}')
print(f'预估页数: {total // 500}')

# ── 引用一致性检查 ──
all_text = ' '.join(s.get('body', '') for s in data['sections'] if s.get('type') == 'text')
cited = set()
for m in re.finditer(r'\[(\d+)\]', all_text):
    cited.add(int(m.group(1)))
max_cite = max(cited) if cited else 0
if max_cite > refs:
    print(f'⚠️ ERROR: 正文引用了 [1]-[{max_cite}] 但只有 {refs} 条参考文献！需补齐至少 {max_cite} 条')
elif refs == 0 and cited:
    print(f'⚠️ ERROR: 参考文献为空但正文使用了 {len(cited)} 个引用标记！')
else:
    print(f'✅ 引用一致性: OK (最大引用 [{max_cite}], 参考文献 {refs} 条)')

# ── 图表维度检查 ──
ok = True
for i, s in enumerate(data['sections']):
    t = s.get('type', '')
    if t == 'chart_bar':
        nc = len(s.get('categories', []))
        for j, sr in enumerate(s.get('series', [])):
            nv = len(sr.get('values', []))
            if nv != nc:
                print(f'⚠️ ERROR: sections[{i}] chart_bar categories={nc} 但 series[{j}].values={nv}')
                ok = False
    elif t == 'chart_pie':
        nl = len(s.get('labels', []))
        nv = len(s.get('values', []))
        if nl != nv:
            print(f'⚠️ ERROR: sections[{i}] chart_pie labels={nl} 但 values={nv}')
            ok = False
    elif t == 'chart_line':
        nx = len(s.get('x_labels', []))
        for j, sr in enumerate(s.get('series', [])):
            nv = len(sr.get('values', []))
            if nv != nx:
                print(f'⚠️ ERROR: sections[{i}] chart_line x_labels={nx} 但 series[{j}].values={nv}')
                ok = False
if ok:
    print('✅ 图表维度: OK')
"
```

**⚠️ 必须在 PDF 生成前运行上述校验。如果输出包含 ERROR，必须先修复再生成 PDF。**

**质量阈值**：
- 总字数 < 5000 → 内容不足，回到 Phase 5 补充
- 任何章节 < 400 字 → 需要扩充
- 参考文献 < 10 → 检查引用是否遗漏
- 引用一致性检查有 ERROR → 必须补齐参考文献或移除多余引用标记
- 图表维度检查有 ERROR → 必须修正数组长度使其一致

**注意**：预估页数仅用于判断内容充足度，**绝对不要**把页码/页数写进 `cover_meta` 或报告封面——实际页数在组装时未知，写入会产生不准确信息。

---

## arXiv API Query 速查

### 搜索字段

| 前缀 | 搜索范围 |
|------|----------|
| `abs:` | 摘要 |
| `ti:` | 标题 |
| `au:` | 作者 |
| `all:` | 所有字段 |
| `cat:` | 分类（如 cs.AI, cs.LG） |

### 组合语法

```
abs:%22liquid+cooling%22+AND+abs:%22data+center%22    # 精确短语 + AND
abs:%22term+A%22+OR+abs:%22term+B%22                  # OR 并集
ti:%22exact+phrase%22+AND+abs:keyword                  # 标题+摘要组合
cat:cs.AI+AND+abs:%22large+language+model%22           # 限定分类
```

### 常用分类代码

| 代码 | 领域 | 代码 | 领域 |
|------|------|------|------|
| cs.AI | 人工智能 | cs.LG | 机器学习 |
| cs.CL | NLP/计算语言学 | cs.CV | 计算机视觉 |
| cs.DC | 分布式计算 | cs.PF | 性能 |
| cs.AR | 体系结构 | cs.SE | 软件工程 |
| eess.SP | 信号处理 | physics.app-ph | 应用物理 |

---

## 质量标准

| 维度 | 要求 |
|------|------|
| 数据源覆盖 | **必须包含**文献检索 + ToolUniverse，Web 搜索推荐启用 |
| 文献检索（**必选**） | arXiv（如适用）候选 40-60 篇精选 12-15 篇；**且**通过 ToolUniverse 调用 PubMed/EuropePMC/OpenAlex 等检索 ≥ 20 篇相关论文 |
| ToolUniverse（**必选**） | 文献检索工具 + 领域专业工具，合计 5-12 次工具调用，数据全部保存 |
| 单篇/单源摘要 | 每个数据源生成结构化摘要 |
| 章节字数 | 每个分析章节 ≥ 1500 字散文段落 |
| 写作风格 | 学术散文，段落 8-10 句，bullet ≤ 5% |
| 引用标注 | 所有事实性陈述标注 `[n]` |
| 数据支撑 | 每章至少 3-5 组量化数据 |
| 报告总字数 | ≥ 8000 字（不含参考文献） |
| 报告格式 | PDF/DOCX，含封面+目录+图表+参考文献 |

---

## 文件组织

```
/home/scienceclaw/sessionid/
├── research_plan.json                # Phase 1 调研计划
├── search_config.json                # Phase 2A arXiv 搜索配置
├── research_papers/                  # Phase 2A arXiv 输出
│   ├── all_candidates.json
│   ├── selected_papers.json
│   ├── {paper_id}.pdf
│   └── {paper_id}.txt
├── research_data/                    # Phase 2B/2C 采集数据
│   ├── uniprot_*.json
│   ├── opentargets_*.json
│   ├── pubmed_*.json
│   ├── web_*.md
│   └── data_summary.md
├── paper_summaries/                  # Phase 4 论文摘要
│   └── summary_{paper_id}.txt
├── data_summaries/                   # Phase 4 数据摘要
│   └── summary_*.txt
├── sections/                         # Phase 5 报告章节
│   ├── executive_summary.txt
│   ├── sec_01_background.txt
│   ├── sec_02_methods.txt
│   ├── ...
│   └── conclusion.txt
├── generate_report.py                # Phase 6 PDF 生成器（从 pdf skill 复制）
├── generate_report.js                # Phase 6 DOCX 生成器（从 docx skill 复制，按需）
├── report_data.json                  # Phase 6 组装后的报告数据
└── final_report.pdf / .docx          # 最终报告
```
