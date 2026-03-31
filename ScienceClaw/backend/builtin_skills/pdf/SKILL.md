---
name: pdf
description: Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, adding watermarks, creating new PDFs, filling PDF forms, encrypting/decrypting PDFs, extracting images, and OCR on scanned PDFs to make them searchable. If the user mentions a .pdf file or asks to produce one, use this skill.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Guide

## Overview

This guide covers essential PDF processing operations using Python libraries and command-line tools. For advanced features, JavaScript libraries, and detailed examples, see REFERENCE.md. If you need to fill out a PDF form, read FORMS.md and follow its instructions.

## Default Output Format for Complex Tasks

When a user's task involves multiple tool calls (web search, data analysis, tool invocations, etc.) and produces substantial research results, but the user has **NOT specified an output format**, you should **default to generating a PDF report** using the template below. This applies to:

- Research tasks that gather information from multiple sources
- Analysis tasks that produce structured findings
- Any multi-step task where the final deliverable is a comprehensive answer

**Do NOT** default to PDF for simple Q&A, quick lookups, or tasks where the user clearly expects a chat response. Use your judgment: if the task took 5+ tool calls and produced rich, structured content, a PDF report is the appropriate default.

When defaulting to PDF output, follow the "Generate PDF Reports" workflow below — use `generate_report.py` with `report_data.json`, NOT the markdown-to-PDF approach.

---

## Quick Start — Choosing the Right Tool for Text Extraction

**Not all extractors are equal.** Pick the right one based on your PDF type:

| PDF Type | Best Tool | Why |
|---|---|---|
| Academic papers (two-column, conference/journal) | `pdftotext -layout` (poppler) | Handles column detection and character spacing reconstruction |
| Simple single-column documents | pdfplumber or pypdf | Good enough, easier to script |
| Scanned PDFs (image-based) | pytesseract + pdf2image | Needs OCR |
| Tables / structured data | pdfplumber | Best table extraction |

### Academic Papers — Use pdftotext First

Most academic PDFs (arXiv, IEEE, ACM, etc.) use two-column layouts and custom font encodings where spaces are implicit (encoded as character spacing, not space characters). Python libraries like `pypdf` and basic `pdfplumber` often produce **merged words** (e.g. `"TheConferenceonAI"` instead of `"The Conference on AI"`).

**Always prefer `pdftotext` from poppler-utils for academic papers:**

```bash
# Best option — preserves layout and column structure
pdftotext -layout input.pdf output.txt

# Alternative — raw text without layout (still handles spacing correctly)
pdftotext input.pdf output.txt
```

If `pdftotext` is not available, use PyMuPDF with sort mode:

```python
import fitz  # PyMuPDF

doc = fitz.open("document.pdf")
for page in doc:
    # sort=True reorders text by reading position (top-to-bottom, left-to-right)
    text = page.get_text("text", sort=True)
    print(text)
```

### Simple Documents — pypdf Quick Start

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

text = ""
for page in reader.pages:
    text += page.extract_text()
```

> **Warning**: pypdf's text extraction is basic. If the output has merged words or garbled column text, switch to `pdftotext -layout`.

## Generate PDF Reports (Data-Driven Template)

**MANDATORY: When creating ANY structured report (research, analysis, summary, etc.), you MUST use the pre-built professional template.** Do NOT write your own PDF generation code using reportlab, fpdf2, or any other library from scratch. The template already handles all styling, CJK fonts, layout, and pagination correctly.

This template produces business-professional quality PDFs with:
- Cover page with metadata table and disclaimer
- **Auto-generated Table of Contents with page numbers**
- Numbered section headings, dense detailed content
- Tables with auto column widths and smart alignment
- References section with numbered citations

### Step 1: Copy the generator to your workspace

**CRITICAL**: You MUST use shell `cp` to copy the script exactly as shown below. Do NOT:
- Write your own PDF generator from scratch
- Use `read_file` + `write_file` (risks stale cached version)
- Modify the generator script in any way

```bash
cp /builtin-skills/pdf/scripts/generate_report.py ./generate_report.py
```

### Step 2: Build `report_data.json`

**Two phases: write section text files, then assemble into JSON.**

**Phase 1 — Write each section as a plain text file** using `write_file`:

For each major section, `read_file` the relevant research_data, then `write_file` the section content directly:
```
read_file("research_data/literature.md")           # refresh data in context
write_file("sections/sec_01_intro.txt", "...")      # write section content
write_file("sections/sec_02_mutations.txt", "...")   # next section
...
```
Each section file should be 1,000-2,000+ words with specific data, citations, and analysis.

**NEVER write a Python script that contains section text as string literals.** The section content goes directly into .txt files via `write_file`, not into Python code. Do NOT write scripts named "generate_sections", "create_content", "build_report" etc. that embed text in Python strings. If a sandbox script fails twice, switch to direct `write_file` calls.

**Writing style — academic research report (CRITICAL):**
- Write continuous flowing prose. Each paragraph: 8--10 sentences following the pattern: topic sentence → supporting evidence with specific data → analysis/comparison → transition to next point.
- Use in-text citations [1], [2] when referencing data. These render as superscript links in the PDF. Do NOT add a "References" list at the end of each chapter — all references go in ONE final `references` section.
- Synthesize across sources: "Study A [1] reported X, while Study B [2] found Y, suggesting that Z."
- Use academic connectives: "Furthermore", "In contrast", "These findings indicate", "Notably", "Taken together".
- NEVER use numbered-point structure (e.g. "1. Topic Title\n\nParagraph. 2. Topic Title\n\nParagraph."). Instead, use `##` subheadings for structure and prose paragraphs for content. The template's `_render_text` correctly renders `##`/`###` as formatted subheadings and `| col1 | col2 |` as PDF tables.
- Bullet lists: max 5% of section, only for short enumerations (e.g. 4-5 drug names).

**Language (CRITICAL):**
- All report content (title, subtitle, section headings, body text, chart labels, table headers, cover metadata) MUST be written in the **user's configured language** as specified in the system prompt's `## Language` section.
- If the user's language is Chinese (`zh`), write the entire report in Chinese; if English (`en`), write in English. Do NOT mix languages unless quoting a proper noun or technical term that has no standard translation.

**Verification (before generating PDF):**
Run a one-liner to count chars per section:
```
python3 -c "import os,glob; [print(f'{f}: {len(open(f).read())} chars') for f in sorted(glob.glob('sections/*.txt'))]; total=sum(len(open(f).read()) for f in glob.glob('sections/*.txt')); print(f'TOTAL: {total} chars, ~{total//500} pages')"
```
If total is under target, do ONE revision: `read_file` data again, then `write_file` to rewrite the thinnest 1-2 sections. Then proceed — no looping.

**Phase 2 — Assemble into JSON** using this standard assembler script:

```python
import json, glob, os

SECTIONS_DIR = "sections"
TITLE = "Report Title"
SUBTITLE = "Subtitle"

# Section config: (file_pattern, heading_number, heading_text, chart_or_None)
# chart: a dict with "type" key (chart_bar, chart_pie, or chart_line) plus type-specific fields.
SECTION_MAP = [
    ("sec_01_*.txt", "1.", "Introduction", None),
    ("sec_02_*.txt", "2.", "Distribution Analysis", {
        "type": "chart_pie",
        "title": "Category Distribution",
        "labels": ["Type A", "Type B", "Type C", "Other"],
        "values": [35, 30, 20, 15]
    }),
    ("sec_03_*.txt", "3.", "Trend Analysis", {
        "type": "chart_line",
        "title": "Yearly Trends",
        "x_labels": ["2020", "2021", "2022", "2023", "2024"],
        "series": [{"name": "Metric", "values": [40, 55, 62, 70, 78]}]
    }),
    ("sec_04_*.txt", "4.", "Comparison", {
        "type": "chart_bar",
        "title": "Key Comparisons",
        "categories": ["Item A", "Item B", "Item C"],
        "series": [{"name": "Score", "values": [85, 72, 91]}]
    }),
    # ... mix chart types: chart_pie for distributions, chart_line for trends, chart_bar for comparisons
]

data = {
    "title": TITLE, "subtitle": SUBTITLE,
    "short_title": TITLE[:40], "report_type": "Research Report",
    "toc": True, "sections": [],
    "cover_meta": [["Report Type", "Research Report"]],
}

for pattern, num, heading, chart in SECTION_MAP:
    matches = sorted(glob.glob(os.path.join(SECTIONS_DIR, pattern)))
    if not matches:
        continue
    body = open(matches[0], encoding="utf-8").read().strip()
    data["sections"].append({"type": "heading", "level": 1, "number": num, "text": heading})
    data["sections"].append({"type": "text", "body": body})
    if chart:
        data["sections"].append(chart)  # chart dict already has "type" key

# Add references section at end
data["sections"].append({"type": "heading", "level": 1, "text": "References"})
data["sections"].append({"type": "references", "items": []})

with open("report_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Generated report_data.json ({len(data['sections'])} sections)")
```

Customize `SECTION_MAP`. Each chart config must include a `"type"` key. **Mix chart types for visual variety (aim for 3-5 charts):**
- `chart_pie` — for proportions/distributions (e.g. mutation type breakdown)
- `chart_line` — for trends over time (e.g. yearly incidence)
- `chart_bar` — for comparisons/rankings (e.g. drug efficacy)

**Adding images (for complex charts only):**

Place each `image` section **immediately after** the `text` section it illustrates:
```python
data["sections"].append({"type": "text", "body": sec2_body})
data["sections"].append({"type": "image", "path": "figures/chart.png", "caption": "Figure 1: ..."})
```

**Content quality requirements**:
- Each `text` body MUST be 3-10 sentences with specific data, citations, and analysis — NOT brief summaries
- Tables MUST have real data with 5+ rows where applicable
- Include specific numbers, percentages, dates, and source references
- Include 2-4 `chart_bar` or `image` sections per report for data visualization

### Step 3: Generate the PDF

```bash
python3 generate_report.py report_data.json output_report.pdf
```

After running the command, verify that `output_report.pdf` actually exists and is non-empty. If the user asked for a PDF, the task is not complete until the file was really created.

### Supported section types

| Type | Required Fields | Optional Fields |
|------|----------------|-----------------|
| `heading` | `text` | `level` (1/2/3), `number` (e.g. "2.1") |
| `text` | `body` (supports Markdown: `##` headings, `- ` bullets, `**bold**`) | `heading` |
| `bullets` | `items` (string array) | `heading` |
| `table` | `headers`, `rows` | `heading`, `col_widths`, `align`, `caption` |
| `kv` | `items` (2-element arrays) | `heading`, `key_width` |
| `image` | `path` | `caption`, `width` (default 150mm) |
| `callout` | `body` | `title` |
| `chart_bar` | `categories`, `series` | `title` |
| `chart_pie` | `labels`, `values` | `title` |
| `chart_line` | `x_labels`, `series` | `title`, `x_title`, `y_title` |
| `references` | `items` (string array) | `heading`, `show_heading` (default: false if no heading given) |
| `page_break` | (none) | |

**Chart types for data visualization (use 3-5 per report, mix types):**
- `chart_bar`: Bar/grouped-bar chart. Good for comparisons, rankings. `series: [{"name": "...", "values": [...]}]`
- `chart_pie`: Pie chart. Good for proportions, distributions. `labels: ["A","B","C"], values: [40,35,25]`
- `chart_line`: Line chart. Good for trends over time. `x_labels: ["2020","2021",...], series: [{"name":"...", "values":[...]}]`

**CRITICAL — Chart dimension constraints (mismatches cause PDF generation to fail):**
- `chart_bar`: `len(categories)` MUST equal `len(series[i].values)` for every series
- `chart_pie`: `len(labels)` MUST equal `len(values)`
- `chart_line`: `len(x_labels)` MUST equal `len(series[i].values)` for every series
- Always count array lengths after constructing chart data to verify they match

### Top-level JSON keys

| Key | Required | Description |
|-----|----------|-------------|
| `title` | Yes | Main report title (cover + header) |
| `subtitle` | No | Subtitle on cover page |
| `short_title` | No | Shorter title for page headers |
| `report_type` | No | Shown in header right side |
| `disclaimer` | No | Disclaimer text at bottom of cover |
| `toc` | No | Generate Table of Contents (default: true) |
| `cover_meta` | No | Array of [key, value] pairs for cover metadata table |
| `sections` | Yes | Array of section objects |

### Writing guidelines for high-quality reports

1. **Be detailed**: Each `text` body should be 3-10 sentences with specific data, not brief summaries
2. **Use numbered headings**: Set `number` field ("1.", "2.1", "3.2.1") for professional structure
3. **Add table captions**: Use `caption` field like "Table 3: Key Financial Metrics (FY2026)"
4. **Include references**: Always end with a `references` section for credibility. Use a `heading` section before it (e.g. "参考文献") and let `references` omit its own heading to avoid duplicates.
5. **In-text citations**: Use `[1]`, `[2]`, `[1,2,3]` markers in `text` body to cite references. The template auto-renders them as superscript links that jump to the corresponding reference entry. Number your citations to match the order in the `references.items` array. **The maximum cited number `[n]` MUST NOT exceed the number of items in `references.items`** — e.g. if you cite `[12]`, you need at least 12 reference entries. If `references.items` is empty, do NOT use any `[n]` markers in the text.
6. **Cover metadata**: Use `cover_meta` to show report type, date, sector, etc. Do NOT include page count or total pages in `cover_meta` — the page count is unknown at assembly time and including it produces inaccurate information.

The template auto-detects CJK characters and installs appropriate fonts.

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata
```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
```

#### Rotate Pages
```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Rotate 90 degrees clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Text and Table Extraction

#### Extract Text with Layout
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

#### Extract Tables
```python
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

#### Advanced Table Extraction
```python
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:  # Check if table is not empty
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

# Combine all tables
if all_tables:
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("extracted_tables.xlsx", index=False)
```

### reportlab - Create PDFs

#### CJK / Chinese Font Support (CRITICAL)

**IMPORTANT**: ReportLab's built-in fonts (Helvetica, Times, Courier) do NOT support Chinese, Japanese, or Korean characters. If your PDF contains ANY non-ASCII text (Chinese, Japanese, Korean, etc.), you MUST register and use a CJK font. Otherwise all CJK characters render as black squares (■).

**MANDATORY for any PDF containing Chinese text — always use this pattern:**

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.fonts import addMapping

# Step 1: Register CJK fonts (do this ONCE at the top of your script)
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))    # Chinese Simplified (Song)
pdfmetrics.registerFont(UnicodeCIDFont('STHeiti-Light'))    # Chinese Simplified (Hei/Bold)

# Step 2: Create styles that use the CJK font
styles = getSampleStyleSheet()
chinese_normal = ParagraphStyle(
    'ChineseNormal', parent=styles['Normal'],
    fontName='STSong-Light', fontSize=10, leading=14,
)
chinese_title = ParagraphStyle(
    'ChineseTitle', parent=styles['Title'],
    fontName='STHeiti-Light', fontSize=18, leading=22,
)
chinese_heading = ParagraphStyle(
    'ChineseHeading', parent=styles['Heading1'],
    fontName='STHeiti-Light', fontSize=14, leading=18,
)
```

Available built-in CJK fonts (no external files needed):
| Font Name | Language | Style |
|-----------|----------|-------|
| `STSong-Light` | Chinese Simplified | Song (serif, body text) |
| `STHeiti-Light` | Chinese Simplified | Hei (sans-serif, headings) |
| `MSung-Light` | Chinese Traditional | Ming (serif) |
| `MHei-Medium` | Chinese Traditional | Hei (sans-serif) |
| `HeiseiMin-W3` | Japanese | Mincho (serif) |
| `HeiseiKakuGo-W5` | Japanese | Gothic (sans-serif) |
| `HYSMyeongJo-Medium` | Korean | Myeongjo (serif) |
| `HYGothic-Medium` | Korean | Gothic (sans-serif) |

**For Canvas-based drawing with Chinese text:**
```python
c = canvas.Canvas("output.pdf", pagesize=A4)
c.setFont('STSong-Light', 12)
c.drawString(100, 700, "中文内容正常显示")
```

#### Basic PDF Creation
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

c.setFont('STSong-Light', 12)
c.drawString(100, height - 100, "Hello World! 你好世界！")

c.line(100, height - 140, 400, height - 140)
c.save()
```

#### Create PDF with Multiple Pages
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
pdfmetrics.registerFont(UnicodeCIDFont('STHeiti-Light'))

styles = getSampleStyleSheet()
cn_title = ParagraphStyle('CNTitle', parent=styles['Title'], fontName='STHeiti-Light', fontSize=18, leading=22)
cn_h1 = ParagraphStyle('CNH1', parent=styles['Heading1'], fontName='STHeiti-Light', fontSize=14, leading=18)
cn_body = ParagraphStyle('CNBody', parent=styles['Normal'], fontName='STSong-Light', fontSize=10, leading=14)

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
story = []

story.append(Paragraph("报告标题", cn_title))
story.append(Spacer(1, 12))
story.append(Paragraph("这是报告的正文内容。" * 20, cn_body))
story.append(PageBreak())

story.append(Paragraph("第二页", cn_h1))
story.append(Paragraph("第二页的内容", cn_body))

doc.build(story)
```

#### Subscripts and Superscripts

**IMPORTANT**: Never use Unicode subscript/superscript characters (₀₁₂₃₄₅₆₇₈₉, ⁰¹²³⁴⁵⁶⁷⁸⁹) in ReportLab PDFs. The built-in fonts do not include these glyphs, causing them to render as solid black boxes.

Instead, use ReportLab's XML markup tags in Paragraph objects:
```python
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()

# Subscripts: use <sub> tag
chemical = Paragraph("H<sub>2</sub>O", styles['Normal'])

# Superscripts: use <super> tag
squared = Paragraph("x<super>2</super> + y<super>2</super>", styles['Normal'])
```

For canvas-drawn text (not Paragraph objects), manually adjust font the size and position rather than using Unicode subscripts/superscripts.

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1  # Rotate page 1 by 90 degrees

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

### pdftk (if available)
```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split
pdftk input.pdf burst

# Rotate
pdftk input.pdf rotate 1east output rotated.pdf
```

## Common Tasks

### Extract Text from Scanned PDFs
```python
# Requires: pip install pytesseract pdf2image
import pytesseract
from pdf2image import convert_from_path

# Convert PDF to images
images = convert_from_path('scanned.pdf')

# OCR each page
text = ""
for i, image in enumerate(images):
    text += f"Page {i+1}:\n"
    text += pytesseract.image_to_string(image)
    text += "\n\n"

print(text)
```

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

# Create watermark (or load existing)
watermark = PdfReader("watermark.pdf").pages[0]

# Apply to all pages
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Extract Images
```bash
# Using pdfimages (poppler-utils)
pdfimages -j input.pdf output_prefix

# This extracts all images as output_prefix-000.jpg, output_prefix-001.jpg, etc.
```

### Password Protection
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Add password
writer.encrypt("userpassword", "ownerpassword")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Extract text (academic/two-column) | **pdftotext** (poppler) | `pdftotext -layout doc.pdf out.txt` |
| Extract text (simple docs) | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Fill PDF forms | pdf-lib or pypdf (see FORMS.md) | See FORMS.md |

## Next Steps

- For advanced pypdfium2 usage, see REFERENCE.md
- For JavaScript libraries (pdf-lib), see REFERENCE.md
- If you need to fill out a PDF form, follow the instructions in FORMS.md
- For troubleshooting guides, see REFERENCE.md
