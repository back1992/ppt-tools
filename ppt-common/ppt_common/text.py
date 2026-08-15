"""
Shared text utilities for PDF processing and CJK language handling.

Consolidates CJK/PDF text handling shared across packages in one place.

Public API:
    is_cjk(text)          — True if text is predominantly CJK
    is_cjk_char(c)        — True if character is CJK or CJK punctuation
    is_cjk_ideograph(c)   — True if character is a CJK ideograph (Han/Kana/Hangul, no punctuation)
    is_cjk_pair(a, b)     — True if either adjacent char is CJK (for line joining)
    merge_pdf_lines(lines)— Merge PDF-extracted lines into proper paragraphs
    extract_page_text(page)   — Raw page text without sub-body (footnote) spans
    split_sentences(text) — Split text into sentences (CJK/Latin aware)
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# CJK character ranges
# ---------------------------------------------------------------------------
#
# Range boundaries are inclusive and defined via chr() so mutation testing
# sees integer mutations (killable by boundary tests) instead of
# provably-equivalent hex-case mutants on "\uXXXX" string literals.

_CJK_PUNCT = "，。！？、；：""''（）《》"  # Fullwidth CJK punctuation

_HAN_LO, _HAN_HI = chr(0x4E00), chr(0x9FFF)        # CJK Unified Ideographs
_KANA_LO, _KANA_HI = chr(0x3040), chr(0x30FF)      # Hiragana + Katakana
_HANGUL_LO, _HANGUL_HI = chr(0xAC00), chr(0xD7AF)  # Hangul Syllables

# PDF extraction artifacts stripped by merge_pdf_lines (chr() for the same
# reason as the range boundaries above).
_BACKSPACE = chr(0x08)
_ZERO_WIDTH_SPACE = chr(0x200B)

# Control characters removed by clean_page (everything C0 except \t \n \r).
# chr() literals keep the codepoints mutation-testable without admitting
# equivalent hex-case mutants.
_PAGE_CONTROL_RE = re.compile(
    "[%s-%s%s%s%s-%s]" % (chr(0x00), chr(0x08), chr(0x0B), chr(0x0C),
                          chr(0x0E), chr(0x1F))
)

# "Chapter N" running header. Character-class casing (instead of
# re.IGNORECASE) so mutmut's string case-swaps change behaviour and are
# killable by the upper/lower-case tests.
_CHAPTER_NUM_RE = re.compile(r'^[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+\s*$')

# Embedded edition header, e.g. 书名（第2版）.
_EDITION_HEADER_RE = re.compile(
    rf'[{_HAN_LO}-{_HAN_HI}]{{2,10}}（第[一二三四五六七八九十\d]+版）'
)


def _in_range(c: str, lo: str, hi: str) -> bool:
    """Return True if *lo* <= *c* <= *hi* (single-character comparison)."""
    return lo <= c <= hi

# ---------------------------------------------------------------------------
# Text sanitization
# ---------------------------------------------------------------------------

# Pattern to match all C0 control characters except newline, tab, carriage return
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
# Pattern to match ISBN-like strings (e.g., '099619-01-66670-7', '978-0-123456-78-9')
# Allow 1-7 digits in each group to handle various ISBN formats
_ISBN_RE = re.compile(r'\b\d{1,7}-\d{1,7}-\d{1,7}-\d{1,7}\b')
# Pattern to match pure digit/hyphen strings
_DIGIT_HYPHEN_RE = re.compile(r'^[\d\-]+$')
# Fragments with no word character at all (letter/digit/CJK): orphan
# punctuation such as "," or "——" must not survive as standalone text
# (they rendered as trivial bullets/text boxes on slides).
_PUNCT_ONLY_RE = re.compile(r'^\W+$')


def sanitize_text(text: str) -> str:
    """Sanitize PDF-extracted text: strip control chars and noise.
    
    Removes:
    - C0 control characters (except newline, tab, carriage return)
    - ISBN-like patterns (e.g., '099619-01-66670-7')
    - Pure digit/hyphen strings (page numbers, list-enumerator residue)
    - Fragments with no word characters at all — orphan punctuation such
      as "," or "——"
    - Leading/trailing whitespace
    """
    text = _CONTROL_CHARS_RE.sub('', text)
    stripped = text.strip()
    if not stripped or _DIGIT_HYPHEN_RE.match(stripped) or _PUNCT_ONLY_RE.match(stripped):
        return ""
    text = _ISBN_RE.sub('', text)
    return text.strip()

# ---------------------------------------------------------------------------
# Compiled regexes for PDF line merging
# ---------------------------------------------------------------------------

# Garbage lines: empty-ish, or short non-CJK non-word fragments
_GARBAGE_RE = re.compile(
    r"^[\s\x08\u200b\u2003\u0c5c\u00a0]*$"
    r"|^[^\u4e00-\u9fff\w]{1,3}$"
)

# Section/chapter headers that always start a new paragraph
_HEADER_RE = re.compile(
    r"^("
    r"第[一二三四五六七八九十百千零\d]+[章节篇部]"
    r"|\d+\.\d+(?:\.\d+)?\s+\S"
    r"|[A-Z]\.\s"
    r"|Chapter\s|Part\s|Section\s"
    r"|（[一二三四五六七八九十]+）"
    r")",
    re.I,
)


# ---------------------------------------------------------------------------
# CJK detection
# ---------------------------------------------------------------------------


def is_cjk_char(c: str) -> bool:
    """Return True if *c* is a CJK character or CJK punctuation."""
    return (
        _in_range(c, _HAN_LO, _HAN_HI)
        or c in _CJK_PUNCT
        or _in_range(c, _KANA_LO, _KANA_HI)
    )


def is_cjk_ideograph(c: str) -> bool:
    """Return True if *c* is a CJK ideograph (Han, Kana, or Hangul).

    Unlike :func:`is_cjk_char`, this excludes CJK punctuation — use it when
    counting content characters (e.g. density metrics) where punctuation
    should not count.
    """
    return (
        _in_range(c, _HAN_LO, _HAN_HI)        # CJK Unified Ideographs
        or _in_range(c, _KANA_LO, _KANA_HI)   # Hiragana + Katakana
        or _in_range(c, _HANGUL_LO, _HANGUL_HI)  # Hangul Syllables
    )


def is_cjk(text: str) -> bool:
    """
    Return True if *text* is predominantly CJK characters.

    Compares the count of CJK ideographs (plus Hiragana/Katakana) against
    the count of ASCII letters.  Used throughout the pipeline to choose
    between Chinese and English prompt templates, output formatting, etc.

    Handles mixed titles like "完形趋向（good form）" by checking if CJK
    characters are present (even if fewer than Latin letters).

    >>> is_cjk("传播学概述")
    True
    >>> is_cjk("Communication Theory Overview")
    False
    >>> is_cjk("完形趋向（good form）")
    True
    """
    cjk = sum(
        1
        for c in text
        if _in_range(c, _HAN_LO, _HAN_HI) or _in_range(c, _KANA_LO, _KANA_HI)
    )
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    
    # If any CJK characters are present, treat as CJK
    # This handles mixed titles like "完形趋向（good form）"
    if cjk > 0:
        return cjk >= latin or cjk >= 3
    return False


def is_cjk_pair(a: str, b: str) -> bool:
    """
    Return True if either character in a pair is CJK.

    When joining two consecutive PDF lines, CJK-to-CJK joins should happen
    *without* an intervening space (e.g. "符号互" + "动" → "符号互动"),
    whereas Latin text needs a space ("hello" + "world" → "hello world").
    """
    return is_cjk_char(a) or is_cjk_char(b)


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------


def split_sentences(text: str, cjk_mode: bool | None = None,
                    min_length: int = 0) -> list[str]:
    """
    Split text into sentences using language-appropriate terminators.

    Canonical implementation — do NOT reimplement sentence splitting
    elsewhere.

    Args:
        text: Text to split.
        cjk_mode: True → CJK terminators (。！？), False → Latin (.!?).
            If None, auto-detect via :func:`is_cjk`.
        min_length: If > 0, only return sentences whose stripped length
            exceeds this value (sentences are stripped in that case).

    Returns:
        List of sentence strings.

    >>> split_sentences("第一句。第二句。")
    ['第一句。', '第二句。']
    >>> split_sentences("First. Second!")
    ['First.', ' Second!']
    """
    if cjk_mode is None:
        cjk_mode = is_cjk(text)
    pattern = r'[^。！？]+[。！？]' if cjk_mode else r'[^.!?]+[.!?]'
    sentences = re.findall(pattern, text)
    if min_length > 0:  # pragma: no mutate
        return [s.strip() for s in sentences if len(s.strip()) > min_length]
    return sentences


# ---------------------------------------------------------------------------
# PDF line merging
# ---------------------------------------------------------------------------

_SENTENCE_ENDS = frozenset('。！？.!?"”)）》')


def merge_pdf_lines(lines: list[str]) -> str:
    """
    Merge PDF-extracted lines into proper paragraphs.

    PDF text extraction often inserts artificial line breaks mid-sentence.
    This function joins lines that belong to the same paragraph while
    preserving real paragraph boundaries:

    * Empty / garbage lines → paragraph break
    * Section headers (``第X章``, ``1.2 Title``, …) → always standalone
    * Lines following a sentence-ending punctuation → new paragraph
    * CJK-to-CJK joins happen without a space; Latin joins with a space

    Returns the merged text as a single string with paragraphs separated
    by ``\\n``.

    >>> merge_pdf_lines(["传播", "学概述"])
    '传播学概述'
    >>> merge_pdf_lines(["hello", "world"])
    'hello world'
    """
    if not lines:
        return ""

    paragraphs: list[str] = []
    current = ""  # pragma: no mutate

    for raw_line in lines:
        line = raw_line.replace(_BACKSPACE, "").replace(_ZERO_WIDTH_SPACE, "").strip()

        # Skip garbage / empty lines (treat as paragraph break)
        if not line or _GARBAGE_RE.match(line):
            if current:
                paragraphs.append(current)
                current = ""  # pragma: no mutate
            continue

        # Section headers are always their own paragraph (extended
        # detection keeps "1 问题：…" / "总结" from gluing onto
        # adjacent paragraphs, which used to hide whole sections from
        # downstream section detection).
        if is_pdf_section_header(line):
            if current:
                paragraphs.append(current)
            paragraphs.append(line)
            current = ""  # pragma: no mutate
            continue

        # First line of a new paragraph
        if not current:
            current = line
            continue

        # Decide: continue current paragraph or start a new one?
        if current[-1] in _SENTENCE_ENDS:
            paragraphs.append(current)
            current = line
        else:
            if is_cjk_pair(current[-1], line[0]):
                current += line
            else:
                current += " " + line

    if current:
        paragraphs.append(current)

    return "\n".join(paragraphs)


# ---------------------------------------------------------------------------
# PDF page cleaning
# ---------------------------------------------------------------------------


def subbody_threshold(blocks, min_ratio: float = 0.85) -> float:
    """
    Font-size cutoff below which spans are footnote/marker noise (TRA-396).

    The modal font size (weighted by span text length) is the body size;
    footnotes, inline footnote markers and page numbers are set smaller.
    Returns 0.0 when blocks carry too little text (sparse pages such as
    title pages, where the modal size is not meaningful).
    """
    weights: dict[float, int] = {}
    lines = 0
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_chars = 0
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text.strip():
                    line_chars += len(text)
                    size = round(span.get("size", 0.0), 1)
                    weights[size] = weights.get(size, 0) + len(text)
            if line_chars:
                lines += 1
    if not weights or lines < 6:
        # Modal size is not meaningful on sparse pages (title pages,
        # section openers); never filter there.
        return 0.0
    modal = max(weights, key=lambda size: (weights[size], size))
    return min_ratio * modal


def extract_page_text(page, min_ratio: float = 0.85) -> str:
    """
    Raw page text with sub-body-size spans dropped (TRA-396).

    Footnote lines (including continuations) vanish entirely and inline
    footnote markers are cut without touching the surrounding body text.
    Feed the result to clean_page for header/page-number cleaning.

    Args:
        page: PyMuPDF (fitz) page object.
        min_ratio: fraction of the modal size below which spans drop.
    """
    blocks = page.get_text("dict")["blocks"]
    threshold = subbody_threshold(blocks, min_ratio)
    lines = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            kept = "".join(
                span.get("text", "")
                for span in line.get("spans", [])
                if span.get("size", 0.0) >= threshold
            )
            if kept.strip():
                lines.append(kept.strip())
    return "\n".join(lines)


# Running header patterns (appear at top/bottom of pages)
_CJK_CHAPTER_PATTERN = re.compile(r'^第.+章\s')


def clean_page(text: str, page_num: int, book_title: str = "", chapter_title: str = "") -> str:
    """
    Clean a PDF page's text, removing artifacts and noise.
    
    Removes:
    - Control characters
    - Page numbers (standalone)
    - Running headers (book title, chapter title)
    - Footnote reference markers
    - Unicode garbage from diagrams/images
    
    Args:
        text: Raw page text
        page_num: Page number (unused, for API compatibility)
        book_title: Book title to filter as running header
        chapter_title: Chapter title to filter as running header
    
    Returns:
        Cleaned page text
    
    Example:
        >>> clean_page("传播学概述\n77\n第二节 定义", 1)
        '传播学概述\n第二节 定义'
    """
    clean_lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Skip standalone page numbers
        if re.match(r'^\d{1,4}$', line):
            continue
        
        # Skip standalone footnote markers
        if re.match(r'^[a-z]$', line):
            continue

        # Skip footnote lines: a single lowercase marker followed by CJK
        # body ("a比如，…" / "a 美 赛佛林…"). Page-bottom footnotes would
        # otherwise merge inline into the body mid-sentence (TRA-396).
        if re.match(rf'^[a-z]\s*[{_HAN_LO}-{_HAN_HI}]', line):
            continue
        
        # Skip running headers
        if book_title and line == book_title:
            continue
        if chapter_title and line == chapter_title:
            continue
        if _CJK_CHAPTER_PATTERN.match(line) and len(line) < 20:
            continue
        if _CHAPTER_NUM_RE.match(line) and len(line) < 30:
            continue
        
        # Clean inline footnote refs (CJK punctuation)
        line = re.sub(r'([。！？）"】])\s*[a-z]\s*$', r'\1', line)
        # Clean inline footnote refs (Latin punctuation)
        line = re.sub(r'([.!?)"\]])\s*[a-z]\s*$', r'\1', line)
        line = re.sub(r'\s+[a-z]$', '', line)
        
        # Clean control chars
        line = _PAGE_CONTROL_RE.sub('', line)
        
        # Strip sequences of non-CJK/non-ASCII characters (diagram garbage).
        # Regression: the allowlist originally omitted / - % & + = ~ and the en
        # dash, so body text like "1/10000", "GB/T 15834", "K-12", "图3-2",
        # "20%" lost those characters to spaces. Box-drawing/block garbage
        # (U+2500+) is still stripped.
        line = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2000-\u206fa-zA-Z0-9\s，。！？、；：""''（）《》【】…—–.,!?;:"\'(){}<>/&%+=~-]+', ' ', line)
        line = re.sub(r'\s+', ' ', line).strip()
        
        # Strip running headers embedded within lines (e.g., "书名（第X版）")
        line = _EDITION_HEADER_RE.sub('', line)
        line = re.sub(r'\s+', ' ', line).strip()
        
        if not line:
            continue
        
        # Skip lines with too many non-CJK/non-ASCII characters (diagram garbage)
        cjk_ascii = sum(1 for c in line if _in_range(c, _HAN_LO, _HAN_HI) or c.isascii())
        if len(line) > 5 and cjk_ascii / len(line) < 0.5:
            continue
        
        clean_lines.append(line)
    
    return '\n'.join(clean_lines)


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

# Section patterns by level
_SECTION_L1 = re.compile(
    r'^(第[一二三四五六七八九十\d]+[章部篇]|'
    r'Chapter\s+\d+|Part\s+\d+)',
    re.I
)

_SECTION_L2 = re.compile(
    r'^(第[一二三四五六七八九十\d]+节|'
    r'\d+\.\d+\s+\S|'
    r'Section\s+\d+)',
    re.I
)

_SECTION_L3 = re.compile(
    r'^\d+\.\s*[\u4e00-\u9fffA-Z]')

# Sentence punctuation never found in real headings; body lines that merely
# START with a heading marker ("第二节所讲的左右感知…，") always carry it
# (TRA-404).
_HEADING_PUNCT_RE = re.compile(r'[，。；！？,;!?]')

# CJK enumerated sub-headings ("一、标题") and short numbered items
# ("1. 标题") — real subsection levels that older detection flattened
# (TRA-398).
CJK_NUM_SUBHEADER_PATTERN = re.compile(r'^[一二三四五六七八九十]+、\S')
SHORT_NUMBERED_ITEM_PATTERN = re.compile(r'^\d{1,2}\.\s*\S')


def is_heading_like(line: str, max_length: int = 30) -> bool:
    """
    Check if a line has the shape of a real heading.

    Real headings are short and free of sentence punctuation; body
    sentences that merely start with a heading marker are neither.

    Args:
        line: Line to check.
        max_length: Maximum heading length.

    Returns:
        True if the line looks like a heading.

    Example:
        >>> is_heading_like("第三节 选择性定律")
        True
        >>> is_heading_like("第二节所讲的左右感知和理解的一系列主观因素，主要是针对编码活动而言的，")
        False
    """
    line = line.strip()
    return 0 < len(line) <= max_length and not _HEADING_PUNCT_RE.search(line)


def is_section_header(line: str, max_length: int = 30) -> bool:
    """
    Check if a line looks like a section header.
    
    Section headers are short lines that match chapter/section patterns.
    
    Args:
        line: Line to check
        max_length: Maximum length to consider as header
    
    Returns:
        True if line appears to be a section header
    
    Example:
        >>> is_section_header("第一节 传播的定义")
        True
        >>> is_section_header("这是一段很长的段落内容，描述了很多细节...")
        False
    """
    if len(line) > max_length:
        return False
    if _HEADING_PUNCT_RE.search(line):
        return False
    return bool(
        _SECTION_L1.match(line) or _SECTION_L2.match(line)
        or _SECTION_L3.match(line) or CJK_NUM_SUBHEADER_PATTERN.match(line)
    )


# ---------------------------------------------------------------------------
# Expose compiled regexes for downstream packages that need them
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Expose compiled regexes for downstream packages that need them
# ---------------------------------------------------------------------------

HEADER_PATTERN = _HEADER_RE
GARBAGE_PATTERN = _GARBAGE_RE

# Real documents number top-level sections as "1 问题：…"
# / "3 编辑制作流程：…" (digit + space + CJK title) and close with bare
# words like "总结" / "参考资料". HEADER_PATTERN (used by clean_page for
# running-header removal) must NOT grow these — a body line like
# "1 问题：…" would then be dropped as a "running header" — so they live
# in separate patterns consumed by paragraph merging and section detection.
# Guards: 1-2 digits (not years), >=2 CJK ideographs after the space
# (rejects fragments like "18 版）"), whole line <=~33 chars (rejects
# sentences that merely start with a number, e.g. "3 个实验表明……").
NUMBERED_CJK_HEADER_PATTERN = re.compile(
    r'^\d{1,2}\s+[\u4e00-\u9fff]{2,}[\u4e00-\u9fff：:，、·（）()"\u201c\u201d\u2018\u2019\s\-—–]{0,18}$'
)
STANDALONE_SECTION_WORD_PATTERN = re.compile(
    r'^(?:摘要|引言|前言|结语|小结|总结|结论|附录|参考文献|参考资料|致谢)$'
)


def is_pdf_section_header(line: str) -> bool:
    """Extended section-header detection.

    Superset of HEADER_PATTERN: also matches numbered CJK headers
    ("2 三层标准体系") and standalone section words ("参考资料"). Use for
    paragraph merging and section detection; do NOT use for running-header
    removal (see clean_page, which must keep HEADER_PATTERN semantics).
    """
    line = line.strip()
    if not line:
        return False
    if _HEADER_RE.match(line):
        # Body sentences that merely start with a section marker are not
        # headings (TRA-404).
        return is_heading_like(line, max_length=40)
    if NUMBERED_CJK_HEADER_PATTERN.match(line):
        return True
    if STANDALONE_SECTION_WORD_PATTERN.match(line):
        return True
    if CJK_NUM_SUBHEADER_PATTERN.match(line):
        return is_heading_like(line)
    if SHORT_NUMBERED_ITEM_PATTERN.match(line):
        return is_heading_like(line, max_length=40)
    return False
