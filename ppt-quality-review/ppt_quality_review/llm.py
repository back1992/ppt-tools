"""LLM boundary for render-level visual QC.

Defines the minimal protocol a vision-capable LLM client must satisfy to
drive ``visual_qc.review_rendered_pages``. ``ppt_common.llm.LLMClient``
satisfies it structurally; external projects implement the single method
with any SDK.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VisionReviewer(Protocol):
    """One method: send a user prompt plus rendered page images, return raw text."""

    def chat_with_images(
        self, user_prompt: str, image_paths: list[str], *, model: str = ""
    ) -> str:
        """Return the raw model response for one rendered page."""
        ...
