"""
Shared tool definitions for Pydantic AI agents.

Provides reusable tool functions that can be registered with agents.
These tools encapsulate common operations like JSON parsing, text formatting,
and validation.

Usage:
    from ppt_common.agents.tools import parse_json_tool, format_citations
    
    agent = Agent(model, tools=[parse_json_tool, format_citations])
"""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_response(raw: str) -> dict | None:
    """Parse a JSON response from an LLM, stripping markdown code fences.
    
    This is a utility function for tools that need to parse JSON from
    LLM responses. It handles common formatting issues like code fences.
    
    Args:
        raw: Raw JSON string (may be wrapped in ```json ... ```)
    
    Returns:
        Parsed dict, or None if parsing fails
    
    Examples:
        >>> parse_json_response('```json\\n{"a": 1}\\n```')
        {'a': 1}
        >>> parse_json_response('not json') is None
        True
    """
    if not raw or not raw.strip():
        return None
    
    text = raw.strip()
    # Strip markdown code fences
    text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    
    return data if isinstance(data, dict) else None


def format_citations(results: list[dict[str, Any]]) -> str:
    """Format search results as a citation string.
    
    Converts a list of search results into a formatted string suitable
    for inclusion in agent responses or tool outputs.
    
    Args:
        results: List of result dicts with 'text', 'chunk_index', 'page', 'score'
    
    Returns:
        Formatted citation string
    
    Examples:
        >>> results = [
        ...     {"text": "Sample text", "chunk_index": 0, "page": 1, "score": 0.95}
        ... ]
        >>> print(format_citations(results))
        [1] Chunk 0 (page 1) (score: 0.95):
        Sample text
    """
    if not results:
        return "No results found."
    
    formatted = []
    for i, result in enumerate(results, 1):
        page_info = f" (page {result.get('page')})" if result.get("page") else ""
        score = result.get("score", 0.0)
        chunk_index = result.get("chunk_index", "?")
        text = result.get("text", "")
        
        formatted.append(
            f"[{i}] Chunk {chunk_index}{page_info} (score: {score:.2f}):\n"
            f"{text}\n"
        )
    
    return "\n".join(formatted)


def truncate_text(text: str, max_chars: int = 1000, suffix: str = "...") -> str:
    """Truncate text to a maximum length with a suffix.
    
    Useful for limiting the size of tool outputs to avoid token limits.
    
    Args:
        text: Text to truncate
        max_chars: Maximum character count (default: 1000)
        suffix: Suffix to append if truncated (default: "...")
    
    Returns:
        Truncated text with suffix if needed
    
    Examples:
        >>> truncate_text("Hello, world!", max_chars=8)
        'Hello,...'
        >>> truncate_text("Short", max_chars=100)
        'Short'
    """
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def validate_required_fields(data: dict[str, Any], required: list[str]) -> list[str]:
    """Validate that required fields are present in a dict.
    
    Args:
        data: Dictionary to validate
        required: List of required field names
    
    Returns:
        List of missing field names (empty if all present)
    
    Examples:
        >>> validate_required_fields({"a": 1, "b": 2}, ["a", "b"])
        []
        >>> validate_required_fields({"a": 1}, ["a", "b"])
        ['b']
    """
    return [field for field in required if field not in data]
