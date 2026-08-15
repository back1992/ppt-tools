"""Render-level VLM visual QC for the SVG pipeline (F1, clean-room).

Design (see docs/design/ppt-svg-quality-upgrade-design.md §3):
- per-page parallel VLM review of rendered PNGs (not whole-deck calls);
- severity tiers: only *blocking* issues trigger feedback re-authoring;
- PNG-hash cache: unchanged pages across attempts are not re-reviewed;
- tolerant parsing (passed tri-state, issues coercion, unknown -> cosmetic).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from ppt_common.llm import parse_llm_json

from .gate import GateResult
from .llm import VisionReviewer

logger = logging.getLogger(__name__)

RUBRIC_VERSION = "4"

# Severity tiers: blocking issues drive re-authoring; cosmetic ones only warn.
SEVERITY: dict[str, str] = {
    "garbled_text": "blocking",
    "tofu_boxes": "blocking",
    "blank_page": "blocking",
    "overflow_clipped": "blocking",
    "content_missing": "blocking",
    "overlap": "cosmetic",
    "contract_violation": "cosmetic",
    "low_quality_artifacts": "cosmetic",
    "parse_error": "cosmetic",
    "render_error": "cosmetic",
}
KNOWN_ISSUES = set(SEVERITY)


class VisualQCError(RuntimeError):
    """Raised in strict mode when blocking issues remain after all attempts."""


@dataclass
class PageReview:
    page_index: int
    passed: bool
    issues: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def blocking(self) -> list[str]:
        return [i for i in self.issues if SEVERITY.get(i) == "blocking"]

    @property
    def cosmetic(self) -> list[str]:
        return [i for i in self.issues if SEVERITY.get(i) != "blocking"]


@dataclass
class VisualReview:
    enabled: bool
    pages: list[PageReview] = field(default_factory=list)
    reason: str = ""

    @property
    def blocking(self) -> list[tuple[int, str]]:
        return [(p.page_index, i) for p in self.pages for i in p.blocking]

    @property
    def cosmetic(self) -> list[tuple[int, str]]:
        return [(p.page_index, i) for p in self.pages for i in p.cosmetic]

    @property
    def passed(self) -> bool:
        return not self.blocking


def _normalize_passed(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "pass", "passed", "1")
    return False


def parse_page_review(raw: str, page_index: int) -> PageReview:
    """Tolerant parse of one page's VLM verdict."""
    data = parse_llm_json(raw or "")
    if not isinstance(data, dict):
        return PageReview(page_index, passed=True, issues=["parse_error"],
                          reason="unparseable review response")
    issues: list[str] = []
    raw_issues = data.get("issues")
    if isinstance(raw_issues, list):
        for item in raw_issues:
            name = str(item).strip()
            if not name:
                continue
            issues.append(name if name in KNOWN_ISSUES else "low_quality_artifacts")
    elif raw_issues:
        name = str(raw_issues).strip()
        issues.append(name if name in KNOWN_ISSUES else "low_quality_artifacts")
    reason = str(data.get("reason") or "").strip()
    missing = data.get("missing")
    if isinstance(missing, list) and missing:
        reason = f"{reason}；未渲染要点: {missing}"
    return PageReview(
        page_index=page_index,
        passed=_normalize_passed(data.get("passed")),
        issues=issues,
        reason=reason,
    )


_REVIEW_PROMPT = """\
你是一位严格的 PPT 幻灯片渲染质检员。下面是一张 1280x720 幻灯片渲染图。
对照该页内容简报与画布契约，仅返回 JSON。

该页内容简报：
{brief}

画布契约要点：1280x720；深色页背景 #0F172A、浅色页 #F8FAFC；强调色 #F97316/#14B8A6/#2563EB；
浅色页应有橙色页头竖条与标题、页脚书名与页码；文字清晰无乱码。

判定标准：
- blocking（passed=false）：garbled_text（乱码/无语义文字）、tofu_boxes（缺字方框）、
  overflow_clipped（文字超出画布或容器被裁切）、blank_page（空白页）、
  content_missing——逐条核对简报编号要点：对每条要点，只要页面渲染了其核心语义
  （概括、改写、提炼、拆成多行均可）即算该条已渲染；换行续行不算新要点。
  在 JSON 中额外返回 "missing": [未渲染要点的编号列表]。
  missing 条数 ≥2、或标题未渲染、或整页空白时 issues 含 content_missing 且 passed=false；
  missing ≤1 时 passed=true（可在 reason 说明）。密度问题（简报本身要点少）不在质检范围。
- cosmetic：overlap（关键元素视觉重叠）、contract_violation（配色/页头页脚违反契约）、
  low_quality_artifacts（伪影、畸形版式）。
- 轻微不完美但可用作演示页时 passed=true。

只返回 JSON：{{"passed": true|false, "issues": ["枚举值"...],
  "missing": [未渲染要点编号...], "reason": "一句话"}}
"""


def review_rendered_pages(
    pages: list[dict],
    page_briefs: list[str],
    client: VisionReviewer | None = None,
    *,
    model: str = "",
    workers: int = 4,
    cache: dict | None = None,
) -> VisualReview:
    """Review rendered pages (renderer records from svg_render.render_svg_dir).

    ``cache`` maps ``(sha256, RUBRIC_VERSION)`` -> PageReview; hits skip the VLM
    call and are reused verbatim (re-author attempts keep unchanged pages free).
    Blank renders (renderer histogram) are flagged blocking without a VLM call.
    """
    cache = cache if cache is not None else {}
    if client is None:
        from ppt_common.llm import LLMClient

        client = LLMClient()
    reviews: list[PageReview | None] = [None] * len(pages)
    to_call: list[tuple[int, dict]] = []

    for idx, rec in enumerate(pages):
        page_index = idx + 1
        if not rec.get("ok"):
            reviews[idx] = PageReview(page_index, passed=True,
                                      issues=["render_error"],
                                      reason=str(rec.get("error") or ""))
            continue
        if rec.get("all_background"):
            reviews[idx] = PageReview(page_index, passed=False,
                                      issues=["blank_page"],
                                      reason="renderer histogram: blank page")
            continue
        key = (rec.get("sha256", ""), RUBRIC_VERSION)
        if key in cache:
            reviews[idx] = cache[key]
            continue
        to_call.append((idx, rec))

    def call_one(item: tuple[int, dict]) -> tuple[int, PageReview]:
        idx, rec = item
        brief = page_briefs[idx] if idx < len(page_briefs) else "(无简报)"
        raw = client.chat_with_images(
            _REVIEW_PROMPT.format(brief=brief),
            [rec["path"]],
            model=model,
        )
        review = parse_page_review(raw, idx + 1)
        return idx, review

    if to_call:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for idx, review in pool.map(call_one, to_call):
                reviews[idx] = review
                rec = pages[idx]
                cache[(rec.get("sha256", ""), RUBRIC_VERSION)] = review

    return VisualReview(enabled=True, pages=[r for r in reviews if r is not None])


def feedback_from_review(review: VisualReview, max_cosmetic: int = 3) -> str:
    """Compose the re-authoring feedback block (blocking first)."""
    lines: list[str] = []
    for page_index, issue in review.blocking:
        lines.append(f"第{page_index}页[blocking] {issue}")
    for page_index, issue in review.cosmetic[:max_cosmetic]:
        lines.append(f"第{page_index}页[cosmetic] {issue}")
    if not lines:
        return ""
    return "【质量反馈】上一版渲染检查发现以下问题，本版必须修正：\n" + "\n".join(lines)


def feedback_from_gate(gate: GateResult | dict) -> str:
    """Extract actionable lines from a static gate result."""
    if isinstance(gate, dict):
        output = gate.get("output", "") or ""
    else:
        output = getattr(gate, "output", "") or ""
    lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(("01.", "02.", "03.", "04.", "05.", "06.", "07.",
                                "08.", "09.", "10.", "11.", "12.")) and (
                "[ERROR]" in stripped or "error" in stripped.lower()):
            lines.append(stripped)
    body = "\n".join(lines[:8]) or output[-800:]
    return "【质量反馈】静态门禁未通过，本版必须修正：\n" + body
