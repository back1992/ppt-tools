# ppt-common Agent Instructions

## Text Sanitization

**ALWAYS use `sanitize_text()`** when processing PDF-extracted text:

```python
from ppt_common.text import sanitize_text

# ✅ Sanitize all PDF text before use
clean_text = sanitize_text(raw_pdf_text)
chapter_title = sanitize_text(pdf_structure.chapter_titles[0])
book_title = sanitize_text(bold_item)
```

**`sanitize_text()` removes**:
- Control characters (`\x08`, `\x0c`, etc.) — PyMuPDF extracts these from fonts
- ISBN patterns (`099619-01-66670-7`) — appear in scanned book covers
- Pure digit strings (`93`, `94`) — page numbers, footnote markers
- Unicode garbage from diagrams

**Why this matters**: Unsanitized text will show `*x0008*` or ISBN numbers in slide titles.

## PDF Structure Extraction

Use `extract_pdf_structure()` for comprehensive extraction:

```python
from ppt_common.pdf_structure import extract_pdf_structure

structure = extract_pdf_structure(pdf_path)

# Access components
chapters = structure.chapter_titles    # 第X章, Chapter N
sections = structure.section_titles    # 第X节, Section N  
bold_text = structure.bold_text        # Bold headings (黑体字)
ordered_lists = structure.ordered_lists  # 1. 2. 3. lists
```

**All extraction functions sanitize text automatically** — no need to call `sanitize_text()` again on these outputs.

## Chinese Numbering Conventions

For CJK content, use these patterns:

**Chapters**: 第一章, 第二章, 第三章...
**Sections**: 第一节, 第二节, 第三节...
**Subsections**: 一、二、三 or (一) (二) (三)
**Points**: 1. 2. 3. or (1) (2) (3)

**Detection regex**:

```python
import re

# Chapter pattern
re.match(r'第[一二三四五六七八九十\d]+[章节]', title)

# Section pattern  
re.match(r'第[一二三四五六七八九十\d]+节', title)

# Subsection pattern (Chinese numerals)
re.match(r'[一二三四五六七八九十]+、', title)
```

## Merging PDF Lines

**Use `merge_pdf_lines()` for paragraph reconstruction**, not naive string joining:

```python
from ppt_common.text import merge_pdf_lines

# ✅ CORRECT: Handles CJK line breaks, punctuation, indentation
paragraphs = merge_pdf_lines(raw_lines)

# ❌ WRONG: Naive join creates broken paragraphs
paragraphs = [" ".join(raw_lines)]  # Don't do this
```

**Why**: PDF text extraction breaks paragraphs at arbitrary widths. `merge_pdf_lines()` intelligently reassembles them by detecting:
- Sentence-ending punctuation (。！？)
- Indentation patterns (  )
- CJK character continuity

## CJK Detection

Use `is_cjk()` to detect CJK content:

```python
from ppt_common.text import is_cjk

# Returns True if >50% of text is CJK
if is_cjk(text):
    # Use CJK-specific formatting
    font = "Microsoft YaHei"
else:
    font = "Calibri"
```

**CJK character ranges**:
- Chinese: `\u4e00-\u9fff`
- Japanese Hiragana/Katakana: `\u3040-\u30ff`
- CJK punctuation: `，。！？、；：""''（）《》`

## Common Gotchas

- **Don't skip sanitization** — even "clean-looking" PDF text may contain hidden control characters
- **Don't use `str.join()` for PDF lines** — use `merge_pdf_lines()` for proper paragraph reconstruction
- **Don't assume ASCII numbering** — CJK content uses Chinese numerals (一二三) not digits (1 2 3)
- **Don't filter bold text by length only** — also filter by font name (黑体, Bold, Heavy) to avoid false positives
