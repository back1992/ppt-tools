"""Content splitter for hierarchical PDF structure."""

import re
from typing import Dict, List, Tuple


def classify_bold_item(item: str) -> Tuple[int, str]:
    """Classify bold text item by hierarchy level.
    
    Returns:
        (level, kind) where:
        - level 0 = chapter (第X章)
        - level 1 = section (第X节)
        - level 2 = subsection (一、二、三)
        - level 3 = point (1. 2. 3.)
    """
    if re.match(r'^第.+[章部篇]', item):
        return 0, "chapter"
    elif re.match(r'^第.+节', item):
        return 1, "section"
    elif re.match(r'^[一二三四五六七八九十]+、', item):
        return 2, "subsection"
    elif re.match(r'^\d+\.', item):
        return 3, "point"
    else:
        return -1, "unknown"


def extract_content_under_heading(
    heading: str,
    full_text: str,
    bold_items: List[str]
) -> str:
    """Extract content between this heading and the next bold item.
    
    Args:
        heading: The bold text heading to search for
        full_text: Complete extracted text
        bold_items: List of all bold text items (for finding boundaries)
    
    Returns:
        Content text under this heading
    """
    # Find this heading in the text
    idx = full_text.find(heading)
    if idx < 0:
        return ""
    
    # Get text after the heading
    text_after = full_text[idx + len(heading):]
    
    # Find the next bold item position
    next_bold_pos = len(text_after)
    for other_item in bold_items:
        if other_item != heading:
            pos = text_after.find(other_item)
            if 0 <= pos < next_bold_pos:
                next_bold_pos = pos
    
    # Extract content up to next bold item
    content = text_after[:next_bold_pos].strip()
    return content


def build_hierarchical_outline(
    bold_items: List[str],
    full_text: str
) -> List[Dict]:
    """Build hierarchical outline from bold text items.
    
    Args:
        bold_items: List of bold text items in document order
        full_text: Complete extracted text
    
    Returns:
        List of outline items with:
        - title: bold text
        - level: hierarchy level (0-3)
        - kind: chapter/section/subsection/point
        - content: text under this heading
        - slide_type: suggested slide type
    """
    outline = []
    
    for item in bold_items:
        level, kind = classify_bold_item(item)
        content = extract_content_under_heading(item, full_text, bold_items)
        
        # Map level to slide type
        slide_type_map = {
            0: "title_slide",
            1: "section_divider",
            2: "content_slide",
            3: "detail_slide",
            -1: "content_slide"
        }
        
        outline.append({
            "title": item,
            "level": level,
            "kind": kind,
            "content": content,
            "content_length": len(content),
            "slide_type": slide_type_map.get(level, "content_slide")
        })
    
    return outline


def split_content_by_bold_headings(
    bold_items: List[str],
    full_text: str
) -> Dict[str, str]:
    """Split full text into chunks by bold headings.
    
    Args:
        bold_items: List of bold text items
        full_text: Complete extracted text
    
    Returns:
        Dict mapping bold_text -> content_under_it
    """
    result = {}
    for item in bold_items:
        content = extract_content_under_heading(item, full_text, bold_items)
        result[item] = content
    return result
