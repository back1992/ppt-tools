"""
Content Density Quality Control for PPT slide descriptions.

Validates that slides have appropriate text density — not too sparse (empty-looking)
and not too dense (text overflow, cognitive overload). Works on slide description
dicts before they are rendered into PPTX.

Supports both CJK (character-based) and Latin (word-based) content.
"""

import logging
from dataclasses import dataclass, field

from ppt_common.text import is_cjk, is_cjk_ideograph

logger = logging.getLogger(__name__)


# ─── Thresholds ────────────────────────────────────────────────────────────
# All thresholds are configurable via the Thresholds dataclass.

@dataclass
class Thresholds:
    """Configurable density thresholds for slide quality control."""

    # Content slides (type="content")
    min_bullets: int = 2
    max_bullets: int = 6
    max_words_per_bullet: int = 20
    warn_words_per_bullet: int = 15
    max_total_words: int = 60
    warn_total_words: int = 45
    min_total_words: int = 4

    # CJK-adjusted thresholds (characters instead of words)
    cjk_min_bullets: int = 2
    cjk_max_bullets: int = 6
    cjk_max_chars_per_bullet: int = 40
    cjk_warn_chars_per_bullet: int = 30
    cjk_max_total_chars: int = 130
    cjk_warn_total_chars: int = 90
    cjk_min_total_chars: int = 8

    # Definition slides
    max_definition_words: int = 80
    min_definition_words: int = 10
    cjk_max_definition_chars: int = 150
    cjk_min_definition_chars: int = 5

    # Quote slides
    max_quote_words: int = 50
    cjk_max_quote_chars: int = 100

    # Outline / summary slides
    max_outline_items: int = 8
    min_outline_items: int = 2

    # Comparison slides
    max_comparison_bullets_per_side: int = 4
    max_comparison_bullet_words: int = 15

    # Overall presentation
    min_content_slide_ratio: float = 0.25
    max_content_slide_ratio: float = 0.65
    max_slide_count: int = 28
    min_slide_count: int = 5


# ─── Data Classes ──────────────────────────────────────────────────────────

@dataclass
class SlideDensityIssue:
    """A single density issue found on a slide."""
    slide_index: int
    slide_type: str
    slide_title: str
    severity: str  # "error" | "warning"
    code: str      # machine-readable code
    message: str   # human-readable description

    def __str__(self):
        prefix = "⚠️" if self.severity == "warning" else "❌"
        return (
            f"{prefix} Slide {self.slide_index} [{self.slide_type}] "
            f"'{self.slide_title[:40]}': {self.message}"
        )


@dataclass
class SlideDensityScore:
    """Density score for a single slide."""
    slide_index: int
    slide_type: str
    slide_title: str
    word_count: int = 0
    bullet_count: int = 0
    avg_words_per_bullet: float = 0.0
    score: float = 1.0  # 0.0 = terrible, 1.0 = perfect
    issues: list[SlideDensityIssue] = field(default_factory=list)


@dataclass
class DensityReport:
    """Overall density quality report for a presentation."""
    total_slides: int = 0
    content_slides: int = 0
    issues: list[SlideDensityIssue] = field(default_factory=list)
    slide_scores: list[SlideDensityScore] = field(default_factory=list)
    overall_score: float = 1.0  # 0.0 = terrible, 1.0 = perfect
    is_passing: bool = True

    @property
    def errors(self) -> list[SlideDensityIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[SlideDensityIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def summary(self) -> str:
        """Return a human-readable summary of the report."""
        lines = [f"Content Density Report: {self.total_slides} slides, score={self.overall_score:.2f}"]
        if self.errors:
            lines.append(f"  ❌ {len(self.errors)} error(s)")
            for err in self.errors[:5]:
                lines.append(f"    {err}")
        if self.warnings:
            lines.append(f"  ⚠️  {len(self.warnings)} warning(s)")
            for warn in self.warnings[:5]:
                lines.append(f"    {warn}")
        if not self.issues:
            lines.append("  ✅ No density issues found")
        return "\n".join(lines)


# ─── Analyzer ──────────────────────────────────────────────────────────────

class ContentDensityAnalyzer:
    """Analyze slide descriptions for content density quality issues."""

    def __init__(self, thresholds: Thresholds | None = None):
        self.thresholds = thresholds or Thresholds()

    def analyze(self, slides: list[dict]) -> DensityReport:
        """Analyze a list of slide description dicts for density issues.

        Args:
            slides: List of slide description dicts, each with at minimum
                    a 'type' field. Content slides should have 'points'.

        Returns:
            DensityReport with per-slide scores and overall assessment.
        """
        report = DensityReport(total_slides=len(slides))
        t = self.thresholds

        # Slide type distribution
        type_counts: dict[str, int] = {}
        for slide in slides:
            stype = slide.get("type", "unknown")
            type_counts[stype] = type_counts.get(stype, 0) + 1

        report.content_slides = type_counts.get("content", 0)

        # Per-slide analysis
        for idx, slide in enumerate(slides):
            slide_type = slide.get("type", "unknown")
            slide_title = slide.get("title", slide.get("term", slide.get("quote", "")))
            is_cjk_slide = self._is_cjk_slide(slide)

            score = SlideDensityScore(
                slide_index=idx,
                slide_type=slide_type,
                slide_title=slide_title,
            )

            if slide_type == "content":
                self._analyze_content_slide(slide, score, is_cjk_slide, t)
            elif slide_type == "definition":
                self._analyze_definition_slide(slide, score, is_cjk_slide, t)
            elif slide_type == "quote":
                self._analyze_quote_slide(slide, score, is_cjk_slide, t)
            elif slide_type in ("outline", "summary"):
                self._analyze_list_slide(slide, score, t)
            elif slide_type == "comparison":
                self._analyze_comparison_slide(slide, score, is_cjk_slide, t)
            elif slide_type in ("image", "figure"):
                self._analyze_image_slide(slide, score, is_cjk_slide, t)

            # Compute slide score (penalize by issue severity)
            score.score = self._compute_slide_score(score)
            report.slide_scores.append(score)
            report.issues.extend(score.issues)

        # Overall distribution checks
        self._analyze_distribution(slides, type_counts, report, t)

        # Compute overall score
        report.overall_score = self._compute_overall_score(report)
        report.is_passing = len(report.errors) == 0

        return report

    # ─── Per-slide analyzers ───────────────────────────────────────────

    def _analyze_content_slide(
        self, slide: dict, score: SlideDensityScore, is_cjk_slide: bool, t: Thresholds
    ):
        points = slide.get("points", [])
        if not isinstance(points, list):
            points = []

        score.bullet_count = len(points)

        if is_cjk_slide:
            # CJK: count characters
            char_counts = [self._count_cjk_chars(str(p)) for p in points]
            total_chars = sum(char_counts)
            score.word_count = total_chars

            # Bullet count
            if len(points) < t.cjk_min_bullets:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="too_few_bullets",
                    message=f"Only {len(points)} bullet(s) — minimum {t.cjk_min_bullets} for content slides",
                ))
            elif len(points) > t.cjk_max_bullets:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="error",
                    code="too_many_bullets",
                    message=f"{len(points)} bullets — maximum {t.cjk_max_bullets} to avoid overflow",
                ))

            # Per-bullet character count
            for i, (point, char_count) in enumerate(zip(points, char_counts)):
                if char_count > t.cjk_max_chars_per_bullet:
                    score.issues.append(SlideDensityIssue(
                        slide_index=score.slide_index,
                        slide_type="content",
                        slide_title=score.slide_title,
                        severity="error",
                        code="bullet_too_long",
                        message=f"Bullet {i+1} has {char_count} chars (max {t.cjk_max_chars_per_bullet}): "
                                f"'{str(point)[:30]}...'",
                    ))
                elif char_count > t.cjk_warn_chars_per_bullet:
                    score.issues.append(SlideDensityIssue(
                        slide_index=score.slide_index,
                        slide_type="content",
                        slide_title=score.slide_title,
                        severity="warning",
                        code="bullet_verbose",
                        message=f"Bullet {i+1} has {char_count} chars (recommended ≤{t.cjk_warn_chars_per_bullet})",
                    ))

            # Total character count
            if total_chars > t.cjk_max_total_chars:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="error",
                    code="slide_too_dense",
                    message=f"Total {total_chars} chars (max {t.cjk_max_total_chars}) — slide will overflow",
                ))
            elif total_chars > t.cjk_warn_total_chars:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="slide_verbose",
                    message=f"Total {total_chars} chars (recommended ≤{t.cjk_warn_total_chars})",
                ))
            elif total_chars < t.cjk_min_total_chars and len(points) > 0:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="slide_too_sparse",
                    message=f"Only {total_chars} chars total — slide may look empty",
                ))

            score.avg_words_per_bullet = (
                total_chars / len(points) if points else 0.0
            )
        else:
            # Latin: count words
            word_counts = [len(str(p).split()) for p in points]
            total_words = sum(word_counts)
            score.word_count = total_words

            # Bullet count
            if len(points) < t.min_bullets:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="too_few_bullets",
                    message=f"Only {len(points)} bullet(s) — minimum {t.min_bullets} for content slides",
                ))
            elif len(points) > t.max_bullets:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="error",
                    code="too_many_bullets",
                    message=f"{len(points)} bullets — maximum {t.max_bullets} to avoid overflow",
                ))

            # Per-bullet word count
            for i, (point, word_count) in enumerate(zip(points, word_counts)):
                if word_count > t.max_words_per_bullet:
                    score.issues.append(SlideDensityIssue(
                        slide_index=score.slide_index,
                        slide_type="content",
                        slide_title=score.slide_title,
                        severity="error",
                        code="bullet_too_long",
                        message=f"Bullet {i+1} has {word_count} words (max {t.max_words_per_bullet}): "
                                f"'{str(point)[:40]}...'",
                    ))
                elif word_count > t.warn_words_per_bullet:
                    score.issues.append(SlideDensityIssue(
                        slide_index=score.slide_index,
                        slide_type="content",
                        slide_title=score.slide_title,
                        severity="warning",
                        code="bullet_verbose",
                        message=f"Bullet {i+1} has {word_count} words (recommended ≤{t.warn_words_per_bullet})",
                    ))

            # Total word count
            if total_words > t.max_total_words:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="error",
                    code="slide_too_dense",
                    message=f"Total {total_words} words (max {t.max_total_words}) — slide will overflow",
                ))
            elif total_words > t.warn_total_words:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="slide_verbose",
                    message=f"Total {total_words} words (recommended ≤{t.warn_total_words})",
                ))
            elif total_words < t.min_total_words and len(points) > 0:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="content",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="slide_too_sparse",
                    message=f"Only {total_words} words total — slide may look empty",
                ))

            score.avg_words_per_bullet = (
                total_words / len(points) if points else 0.0
            )

    def _analyze_definition_slide(
        self, slide: dict, score: SlideDensityScore, is_cjk_slide: bool, t: Thresholds
    ):
        definition = slide.get("definition", "")
        term = slide.get("term", "")

        if is_cjk_slide:
            char_count = self._count_cjk_chars(definition)
            score.word_count = char_count

            if char_count > t.cjk_max_definition_chars:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="definition",
                    slide_title=term,
                    severity="error",
                    code="definition_too_long",
                    message=f"Definition has {char_count} chars (max {t.cjk_max_definition_chars})",
                ))
            elif char_count < t.cjk_min_definition_chars and definition:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="definition",
                    slide_title=term,
                    severity="warning",
                    code="definition_too_short",
                    message=f"Definition has only {char_count} chars — may be insufficient",
                ))
        else:
            word_count = len(definition.split()) if definition else 0
            score.word_count = word_count

            if word_count > t.max_definition_words:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="definition",
                    slide_title=term,
                    severity="error",
                    code="definition_too_long",
                    message=f"Definition has {word_count} words (max {t.max_definition_words})",
                ))
            elif word_count < t.min_definition_words and definition:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="definition",
                    slide_title=term,
                    severity="warning",
                    code="definition_too_short",
                    message=f"Definition has only {word_count} words — may be insufficient",
                ))

    def _analyze_quote_slide(
        self, slide: dict, score: SlideDensityScore, is_cjk_slide: bool, t: Thresholds
    ):
        quote = slide.get("quote", "")

        if is_cjk_slide:
            char_count = self._count_cjk_chars(quote)
            score.word_count = char_count

            if char_count > t.cjk_max_quote_chars:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="quote",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="quote_too_long",
                    message=f"Quote has {char_count} chars (recommended ≤{t.cjk_max_quote_chars})",
                ))
        else:
            word_count = len(quote.split()) if quote else 0
            score.word_count = word_count

            if word_count > t.max_quote_words:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="quote",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="quote_too_long",
                    message=f"Quote has {word_count} words (recommended ≤{t.max_quote_words})",
                ))

    def _analyze_list_slide(self, slide: dict, score: SlideDensityScore, t: Thresholds):
        items = slide.get("items", [])
        if not isinstance(items, list):
            items = []

        score.bullet_count = len(items)

        if len(items) > t.max_outline_items:
            score.issues.append(SlideDensityIssue(
                slide_index=score.slide_index,
                slide_type=slide.get("type", "outline"),
                slide_title=score.slide_title,
                severity="error",
                code="too_many_items",
                message=f"{len(items)} items (max {t.max_outline_items}) — will overflow",
            ))
        elif len(items) < t.min_outline_items and len(items) > 0:
            score.issues.append(SlideDensityIssue(
                slide_index=score.slide_index,
                slide_type=slide.get("type", "outline"),
                slide_title=score.slide_title,
                severity="warning",
                code="too_few_items",
                message=f"Only {len(items)} item(s) — outline/summary may be too sparse",
            ))

    def _analyze_comparison_slide(
        self, slide: dict, score: SlideDensityScore, is_cjk_slide: bool, t: Thresholds
    ):
        left_points = slide.get("left_points", [])
        right_points = slide.get("right_points", [])
        if not isinstance(left_points, list):
            left_points = []
        if not isinstance(right_points, list):
            right_points = []

        score.bullet_count = len(left_points) + len(right_points)

        # Check per-side bullet counts
        for side_name, side_points in [("left", left_points), ("right", right_points)]:
            if len(side_points) > t.max_comparison_bullets_per_side:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="comparison",
                    slide_title=score.slide_title,
                    severity="error",
                    code=f"{side_name}_too_many_bullets",
                    message=f"{side_name.capitalize()} side has {len(side_points)} bullets "
                            f"(max {t.max_comparison_bullets_per_side})",
                ))

        # Check balance between sides
        if left_points and right_points:
            diff = abs(len(left_points) - len(right_points))
            if diff > 2:
                score.issues.append(SlideDensityIssue(
                    slide_index=score.slide_index,
                    slide_type="comparison",
                    slide_title=score.slide_title,
                    severity="warning",
                    code="unbalanced_sides",
                    message=f"Unbalanced: left={len(left_points)}, right={len(right_points)} bullets",
                ))

    def _analyze_image_slide(
        self, slide: dict, score: SlideDensityScore, is_cjk_slide: bool, t: Thresholds
    ):
        """Image slides should have minimal text — title + short context."""
        context_points = slide.get("context_points", slide.get("points", []))
        if not isinstance(context_points, list):
            context_points = []

        score.bullet_count = len(context_points)

        if len(context_points) > 4:
            score.issues.append(SlideDensityIssue(
                slide_index=score.slide_index,
                slide_type="image",
                slide_title=score.slide_title,
                severity="warning",
                code="image_too_many_points",
                message=f"Image slide has {len(context_points)} context points — "
                        f"recommended ≤4 to leave room for the image",
            ))

    # ─── Distribution analysis ─────────────────────────────────────────

    def _analyze_distribution(
        self, slides: list[dict], type_counts: dict[str, int],
        report: DensityReport, t: Thresholds
    ):
        """Check overall slide type distribution and total count."""
        total = report.total_slides
        if total == 0:
            return

        # Total slide count
        if total > t.max_slide_count:
            report.issues.append(SlideDensityIssue(
                slide_index=-1,
                slide_type="presentation",
                slide_title="(overall)",
                severity="error",
                code="too_many_slides",
                message=f"{total} slides (max {t.max_slide_count})",
            ))
        elif total < t.min_slide_count:
            report.issues.append(SlideDensityIssue(
                slide_index=-1,
                slide_type="presentation",
                slide_title="(overall)",
                severity="warning",
                code="too_few_slides",
                message=f"Only {total} slides (minimum {t.min_slide_count} recommended)",
            ))

        # Content slide ratio
        content_count = type_counts.get("content", 0)
        # Exclude title/outline/summary from denominator for ratio calc
        content_eligible = total - type_counts.get("title", 0) - type_counts.get("summary", 0)
        if content_eligible > 0:
            ratio = content_count / content_eligible
            if ratio < t.min_content_slide_ratio:
                report.issues.append(SlideDensityIssue(
                    slide_index=-1,
                    slide_type="presentation",
                    slide_title="(overall)",
                    severity="warning",
                    code="low_content_ratio",
                    message=f"Content slides are only {ratio:.0%} of non-title slides "
                            f"(recommended ≥{t.min_content_slide_ratio:.0%})",
                ))
            elif ratio > t.max_content_slide_ratio:
                report.issues.append(SlideDensityIssue(
                    slide_index=-1,
                    slide_type="presentation",
                    slide_title="(overall)",
                    severity="warning",
                    code="high_content_ratio",
                    message=f"Content slides are {ratio:.0%} of non-title slides — "
                            f"consider adding definition, quote, or comparison slides for variety",
                ))

    # ─── Scoring ───────────────────────────────────────────────────────

    @staticmethod
    def _compute_slide_score(score: SlideDensityScore) -> float:
        """Compute a 0.0-1.0 score for a single slide based on its issues."""
        if not score.issues:
            return 1.0

        penalty = 0.0
        for issue in score.issues:
            if issue.severity == "error":
                penalty += 0.3
            elif issue.severity == "warning":
                penalty += 0.1

        return max(0.0, 1.0 - penalty)

    @staticmethod
    def _compute_overall_score(report: DensityReport) -> float:
        """Compute overall presentation score from slide scores and distribution issues."""
        if not report.slide_scores:
            return 1.0

        slide_avg = sum(s.score for s in report.slide_scores) / len(report.slide_scores)

        # Additional penalty for distribution-level issues
        dist_penalty = sum(
            0.15 if i.severity == "error" else 0.05
            for i in report.issues
            if i.slide_index == -1
        )

        return max(0.0, slide_avg - dist_penalty)

    # ─── Utilities ─────────────────────────────────────────────────────

    @staticmethod
    def _is_cjk_slide(slide: dict) -> bool:
        """Detect if a slide's primary content is CJK."""
        # Check title, points, definition, quote — whichever has content
        for key in ("title", "term", "quote", "definition"):
            text = slide.get(key, "")
            if text and is_cjk(text):
                return True

        points = slide.get("points", [])
        if isinstance(points, list):
            combined = " ".join(str(p) for p in points[:3])
            if combined and is_cjk(combined):
                return True

        return False

    @staticmethod
    def _count_cjk_chars(text: str) -> int:
        """Count CJK characters in text (ignoring spaces and punctuation)."""
        if not text:
            return 0
        # Count only CJK characters + ASCII words (each word counts as 1)
        cjk_count = 0
        ascii_words = 0
        for char in text:
            if is_cjk_ideograph(char):
                cjk_count += 1
            elif char.isascii() and char.isalpha():
                # ASCII letters will be counted as part of words
                pass

        # Count ASCII words separately
        ascii_text = "".join(c if c.isascii() else " " for c in text)
        ascii_words = len([w for w in ascii_text.split() if w.isalpha()])

        return cjk_count + ascii_words


# ─── Convenience function ──────────────────────────────────────────────────

def analyze_content_density(
    slides: list[dict],
    thresholds: Thresholds | None = None,
) -> DensityReport:
    """Convenience function to analyze slide descriptions for content density.

    Args:
        slides: List of slide description dicts
        thresholds: Optional custom thresholds

    Returns:
        DensityReport with issues and scores
    """
    analyzer = ContentDensityAnalyzer(thresholds=thresholds)
    return analyzer.analyze(slides)
