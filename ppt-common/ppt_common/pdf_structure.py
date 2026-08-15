"""
PDF Structure Extraction - reusable primitives for analyzing PDF document structure.

Provides utilities to extract:
- Chapter titles (第X章, Chapter N)
- Section titles (第X节, Section N, numbered headings)
- Bold text (黑体字, bold fonts)
- Ordered lists (numbered items)

This module is designed to be shared across packages for consistent
PDF structure analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from .text import sanitize_text
from typing import List, Optional

import fitz


@dataclass
class PDFStructure:
    """Container for extracted PDF structural elements.
    
    Attributes:
        chapter_titles: List of chapter-level titles (e.g., 第一章, Chapter 1)
        section_titles: List of section-level titles (e.g., 第一节, Section 1.1)
        bold_text: List of bold/highlighted text spans (often key terms)
        ordered_lists: List of ordered lists found in document
        pdf_path: Source PDF file path
    """
    chapter_titles: List[str] = field(default_factory=list)
    section_titles: List[str] = field(default_factory=list)
    bold_text: List[str] = field(default_factory=list)
    ordered_lists: List[List[str]] = field(default_factory=list)
    pdf_path: str = ""
    
    def summary(self) -> dict:
        """Return summary statistics of extracted structure."""
        return {
            "chapters": len(self.chapter_titles),
            "sections": len(self.section_titles),
            "bold_items": len(self.bold_text),
            "lists": len(self.ordered_lists),
            "pdf_path": self.pdf_path,
        }


# ---------------------------------------------------------------------------
# Regex patterns for chapter/section detection
# ---------------------------------------------------------------------------

_CHAPTER_PATTERN = re.compile(
    r'^(第[一二三四五六七八九十百千零\d]+[章部篇]|'
    r'Chapter\s+\d+|Part\s+\d+)',
    re.I
)

_SECTION_PATTERN = re.compile(
    r'^(第[一二三四五六七八九十百千零\d]+节|'
    r'\d+\.\d+(?:\.\d+)?\s+\S|'
    r'\d{1,2}\.\s+[A-Z\u4e00-\u9fff]|'
    r'Section\s+\d+)',
    re.I
)


def extract_chapter_titles(pdf_path: str, min_font_size: float = 14.0) -> List[str]:
    """
    Extract chapter-level titles from PDF.
    
    Detects lines matching chapter patterns (第X章, Chapter N) that use
    larger font sizes, indicating they are actual chapter headings.
    
    Args:
        pdf_path: Path to PDF file
        min_font_size: Minimum font size to consider as chapter title
    
    Returns:
        List of chapter title strings
    
    Example:
        >>> titles = extract_chapter_titles("textbook.pdf")
        >>> print(titles)
        ['第一章 传播概述', '第二章 传播模式']
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    titles = []
    doc = fitz.open(str(pdf_path))
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    # Reconstruct line text
                    line_text = ""
                    max_font_size = 0.0
                    
                    for span in line["spans"]:
                        line_text += span["text"]
                        max_font_size = max(max_font_size, span["size"])
                    
                    line_text = line_text.strip()
                    # Remove backspace characters
                    line_text = sanitize_text(line_text)
                    
                    # Check if this is a chapter title
                    if (_CHAPTER_PATTERN.match(line_text) and 
                        max_font_size >= min_font_size):
                        titles.append(line_text)
    finally:
        doc.close()
    
    return titles


def extract_section_titles(pdf_path: str, min_font_size: float = 12.0) -> List[str]:
    """
    Extract section-level titles from PDF.
    
    Detects lines matching section patterns (第X节, 1.1 Title, Section N)
    with appropriate font sizes.
    
    Args:
        pdf_path: Path to PDF file
        min_font_size: Minimum font size to consider as section title
    
    Returns:
        List of section title strings
    
    Example:
        >>> titles = extract_section_titles("textbook.pdf")
        >>> print(titles)
        ['第一节 传播的定义', '第二节 传播要素', '1.1 传播者']
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    titles = []
    doc = fitz.open(str(pdf_path))
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    line_text = ""
                    max_font_size = 0.0
                    
                    for span in line["spans"]:
                        line_text += span["text"]
                        max_font_size = max(max_font_size, span["size"])
                    
                    line_text = line_text.strip()
                    # Remove backspace characters
                    line_text = sanitize_text(line_text)
                    
                    # Check if this is a section title
                    if (_SECTION_PATTERN.match(line_text) and 
                        max_font_size >= min_font_size):
                        titles.append(line_text)
    finally:
        doc.close()
    
    return titles


# Default bold keywords for both English and Chinese fonts
DEFAULT_BOLD_KEYWORDS = [
    # English bold fonts
    "bold", "black", "heavy",
    # Chinese bold fonts (黑体 variants)
    "ht", "hei",  # 黑体 (heiti)
    "yahei",       # 微软雅黑
    "zhongsong",   # 中宋
    "songti-sc-bold",
]


def extract_bold_text(
    pdf_path: str, 
    min_length: int = 2, 
    max_length: int = 50,
    bold_keywords: Optional[List[str]] = None
) -> List[str]:
    """
    Extract bold/highlighted text from PDF.
    
    Detects text spans using bold fonts (黑体, Bold, Heavy) which often
    indicate key terms, definitions, or important concepts.
    
    Args:
        pdf_path: Path to PDF file
        min_length: Minimum text length to include
        max_length: Maximum text length to include
        bold_keywords: Font name keywords indicating bold.
            Default includes English (bold, black, heavy) and Chinese
            (ht, hei, yahei, zhongsong) bold font indicators.
    
    Returns:
        List of bold text strings
    
    Example:
        >>> bold = extract_bold_text("textbook.pdf")
        >>> print(bold)
        ['编码', '译码', '传播模式']
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    if bold_keywords is None:
        bold_keywords = DEFAULT_BOLD_KEYWORDS
    
    bold_items = []
    doc = fitz.open(str(pdf_path))
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    # Check if this line has any bold spans
                    has_bold = False
                    bold_text_parts = []
                    
                    for span in line["spans"]:
                        font_name = span["font"].lower()
                        is_bold = any(keyword in font_name for keyword in bold_keywords)
                        
                        if is_bold:
                            has_bold = True
                            # Merge all spans in the line that are bold
                            text = span["text"]
                            bold_text_parts.append(text)
                    
                    # If the line has bold text, merge all bold spans
                    if has_bold and bold_text_parts:
                        # Join all bold parts and clean up
                        merged_text = "".join(bold_text_parts).strip()
                        # Remove backspace characters
                        merged_text = sanitize_text(merged_text)
                        
                        # Filter by length and skip pure digits (page numbers)
                        if min_length <= len(merged_text) <= max_length:
                            bold_items.append(merged_text)
    finally:
        doc.close()
    
    # Remove duplicates while preserving order
    seen = set()
    unique_items = []
    for item in bold_items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    
    return unique_items


# Pattern for numbered list items
_LIST_ITEM_PATTERN = re.compile(
    r'^(\d+[.)、]|'           # 1. 2) 3、
    r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|'  # circled numbers
    r'[a-zA-Z][.)])'          # a. b) A. B)
)


def extract_ordered_lists(pdf_path: str, min_items: int = 2) -> List[List[str]]:
    """
    Extract ordered lists from PDF.
    
    Detects consecutive numbered lines (1., 2., 3. or ①, ②, ③) that
    form ordered lists.
    
    Args:
        pdf_path: Path to PDF file
        min_items: Minimum items to consider as a list
    
    Returns:
        List of lists, where each inner list contains list items
    
    Example:
        >>> lists = extract_ordered_lists("textbook.pdf")
        >>> print(lists)
        [['1. 传播者', '2. 受传者', '3. 信息']]
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    all_lists = []
    doc = fitz.open(str(pdf_path))
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            current_list = []
            
            for block in blocks:
                if "lines" not in block:
                    # End of list if we hit a non-text block
                    if len(current_list) >= min_items:
                        all_lists.append(current_list)
                    current_list = []
                    continue
                    
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    line_text = line_text.strip()
                    
                    if not line_text:
                        continue
                    
                    # Check if this is a list item
                    if _LIST_ITEM_PATTERN.match(line_text):
                        current_list.append(line_text)
                    else:
                        # End of list
                        if len(current_list) >= min_items:
                            all_lists.append(current_list)
                        current_list = []
            
            # Handle list at end of page
            if len(current_list) >= min_items:
                all_lists.append(current_list)
    finally:
        doc.close()
    
    return all_lists


def extract_pdf_structure(
    pdf_path: str,
    chapter_min_font: float = 14.0,
    section_min_font: float = 12.0,
    bold_min_length: int = 2,
    bold_max_length: int = 50,
    list_min_items: int = 2,
) -> PDFStructure:
    """
    Extract all structural elements from PDF in one pass.
    
    Convenience function that calls all extraction functions and
    returns a PDFStructure object containing all results.
    
    Args:
        pdf_path: Path to PDF file
        chapter_min_font: Minimum font size for chapter titles
        section_min_font: Minimum font size for section titles
        bold_min_length: Minimum length for bold text
        bold_max_length: Maximum length for bold text
        list_min_items: Minimum items for ordered lists
    
    Returns:
        PDFStructure object with all extracted elements
    
    Example:
        >>> structure = extract_pdf_structure("textbook.pdf")
        >>> print(structure.summary())
        {'chapters': 3, 'sections': 8, 'bold_items': 15, 'lists': 2}
    """
    return PDFStructure(
        chapter_titles=extract_chapter_titles(pdf_path, chapter_min_font),
        section_titles=extract_section_titles(pdf_path, section_min_font),
        bold_text=extract_bold_text(pdf_path, bold_min_length, bold_max_length),
        ordered_lists=extract_ordered_lists(pdf_path, list_min_items),
        pdf_path=pdf_path,
    )
