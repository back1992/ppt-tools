"""
ppt-common — shared utilities for slide-deck generation packages.

Modules:
    text            — CJK detection, PDF line merging, section header patterns
    text_metrics    — text width estimation, font-size fitting, line wrapping
    llm             — Unified OpenAI-compatible LLM client (DashScope / Qwen)
    pdf_structure   — PDF structure extraction (chapters, sections, bold text, lists)
    agents          — Pydantic AI agent integration (optional, requires [agents])

Usage:
    from ppt_common.text import is_cjk, merge_pdf_lines
    from ppt_common.text_metrics import estimate_text_width, fit_font_size, wrap_text
    from ppt_common.llm import LLMClient, parse_llm_json
    from ppt_common.pdf_structure import PDFStructure, extract_pdf_structure
    from ppt_common.agents import AgentFactory, get_default_model  # requires [agents]
"""

from ppt_common.text import (
    is_cjk,
    is_cjk_char,
    is_cjk_pair,
    merge_pdf_lines,
    clean_page,
    extract_page_text,
    is_section_header,
    is_heading_like,
)

__all__ = [
    # text utilities
    "is_cjk",
    "is_cjk_char",
    "is_cjk_pair",
    "merge_pdf_lines",
    "clean_page",
    "extract_page_text",
    "is_section_header",
    "is_heading_like",
]

# PDF structure (optional — requires PyMuPDF, which lightweight consumers
# of downstream packages like ppt-quality-review may not have installed).
try:
    from ppt_common.pdf_structure import (
        PDFStructure,
        extract_chapter_titles,
        extract_section_titles,
        extract_bold_text,
        extract_ordered_lists,
        extract_pdf_structure,
    )
    __all__.extend([
        "PDFStructure",
        "extract_chapter_titles",
        "extract_section_titles",
        "extract_bold_text",
        "extract_ordered_lists",
        "extract_pdf_structure",
    ])
except ImportError:
    pass

# Pydantic AI agents (optional — requires [agents] extra)
try:
    from ppt_common.agents import (
        AgentFactory,
        get_default_model,
        get_model,
        BaseDeps,
        UserDeps,
        DocumentDeps,
        ConversationDeps,
    )
    __all__.extend([
        "AgentFactory",
        "get_default_model",
        "get_model",
        "BaseDeps",
        "UserDeps",
        "DocumentDeps",
        "ConversationDeps",
    ])
except ImportError:
    pass

__version__ = "1.0.0"
