"""
5D Quality Framework for PPT slide descriptions.

Extends the 4D framework with a Visual dimension that checks image density
and visual richness of the presentation.

Evaluates presentations across five dimensions:
1. Structure  - Logical slide order, progression, completeness
2. Density    - Content density (delegates to ContentDensityAnalyzer)
3. CRAP       - Design principles (Contrast, Repetition, Alignment, Proximity)
4. Scene      - Context/audience appropriateness
5. Visual     - Image density and visual richness (NEW)

Each dimension produces a score (0.0-1.0) and a list of issues.
The overall QualityReport aggregates all five dimensions.
"""

import logging
import sys
from dataclasses import dataclass, field

from .quality_4d import (
    QualityIssue, DimensionScore, QualityReport,
    QualityAnalyzer4D,
)

logger = logging.getLogger(__name__)


# ─── Visual Quality Checker ──────────────────────────────────────────────

class VisualQualityChecker:
    """Check visual richness of presentation."""

    MIN_IMAGE_RATIO = 0.3  # 1 image per 3 slides
    MIN_TOTAL_IMAGES = 2

    def validate(self, slides: list[dict]) -> DimensionScore:
        """
        Check image-to-slide ratio and flag text-heavy slides without visuals.

        Args:
            slides: List of slide description dicts

        Returns:
            DimensionScore for the visual dimension
        """
        issues = []

        # Count slides with images
        slides_with_images = sum(
            1 for s in slides
            if s.get("image_path") or s.get("type") == "figure"
        )
        total_slides = len(slides)

        if total_slides == 0:
            return DimensionScore(
                dimension="visual",
                score=1.0,
                issues=[],
                details={
                    "slides_with_images": 0,
                    "total_slides": 0,
                    "image_ratio": 0.0,
                },
            )

        ratio = slides_with_images / total_slides

        # Check overall image ratio
        if ratio < self.MIN_IMAGE_RATIO:
            issues.append(QualityIssue(
                dimension="visual",
                severity="warning",
                code="low_image_ratio",
                message=(
                    f"Only {ratio:.0%} of slides have images "
                    f"(recommended ≥{self.MIN_IMAGE_RATIO:.0%})"
                ),
            ))

        # Check minimum total images
        if slides_with_images < self.MIN_TOTAL_IMAGES:
            issues.append(QualityIssue(
                dimension="visual",
                severity="warning",
                code="too_few_images",
                message=(
                    f"Presentation has only {slides_with_images} images "
                    f"(minimum {self.MIN_TOTAL_IMAGES} recommended)"
                ),
            ))

        # Check for text-heavy content slides without images
        for i, slide in enumerate(slides):
            slide_type = slide.get("type", "content")
            has_image = bool(slide.get("image_path") or slide_type == "figure")

            if slide_type == "content" and not has_image:
                # Count text length
                points = slide.get("points", [])
                text_length = sum(len(str(p)) for p in points)

                if text_length > 200:
                    issues.append(QualityIssue(
                        dimension="visual",
                        severity="info",
                        code="text_heavy_no_image",
                        message=(
                            f"Content slide has {text_length} chars of text "
                            f"but no image — consider adding a visual"
                        ),
                        slide_index=i,
                    ))

        # Deck-level theme rhythm (shadow/measure-only).
        # The rhythm check lives in the optional companion package
        # ``ppt_generator`` (a generation concern); it is skipped when that
        # package is not installed — standalone consumers still get every
        # per-slide check.
        rhythm_details: dict = {}
        try:
            from ppt_generator.theme_rhythm import check_rhythm
        except ImportError as exc:
            # Skip only when ppt_generator itself is absent. CPython reports
            # exc.name == "ppt_generator" when the package is missing outright,
            # but exc.name == "ppt_generator.theme_rhythm" when a blocked/None
            # sys.modules entry halts resolution ("'ppt_generator' is not a
            # package"), so the parent's sys.modules entry decides that case.
            # Real breakage inside the import chain (missing transitive deps,
            # deleted submodule) must surface.
            name = getattr(exc, "name", None)
            parent_blocked = sys.modules.get("ppt_generator") is None
            if name != "ppt_generator" and not (
                name == "ppt_generator.theme_rhythm" and parent_blocked
            ):
                raise
            logger.debug("theme_rhythm unavailable; skipping rhythm check")
        else:
            rhythm = check_rhythm(slides)
            issues.extend(rhythm.issues)
            rhythm_details = rhythm.details

        # Calculate score
        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.3
            elif issue.severity == "warning":
                score -= 0.15
            else:
                score -= 0.05

        return DimensionScore(
            dimension="visual",
            score=max(0.0, score),
            issues=issues,
            details={
                "slides_with_images": slides_with_images,
                "total_slides": total_slides,
                "image_ratio": round(ratio, 3),
                "rhythm": rhythm_details,
            },
        )


# ─── 5D Quality Report ──────────────────────────────────────────────────

@dataclass
class QualityReport5D:
    """Overall 5D quality report for a presentation."""
    structure: DimensionScore = field(default_factory=lambda: DimensionScore("structure", 1.0))
    density: DimensionScore = field(default_factory=lambda: DimensionScore("density", 1.0))
    crap: DimensionScore = field(default_factory=lambda: DimensionScore("crap", 1.0))
    scene: DimensionScore = field(default_factory=lambda: DimensionScore("scene", 1.0))
    visual: DimensionScore = field(default_factory=lambda: DimensionScore("visual", 1.0))

    @property
    def overall_score(self) -> float:
        """Weighted average of all five dimensions."""
        weights = {
            "structure": 0.20,
            "density": 0.25,
            "crap": 0.20,
            "scene": 0.15,
            "visual": 0.20,
        }
        return (
            self.structure.score * weights["structure"]
            + self.density.score * weights["density"]
            + self.crap.score * weights["crap"]
            + self.scene.score * weights["scene"]
            + self.visual.score * weights["visual"]
        )

    @property
    def all_issues(self) -> list[QualityIssue]:
        return (
            self.structure.issues
            + self.density.issues
            + self.crap.issues
            + self.scene.issues
            + self.visual.issues
        )

    @property
    def errors(self) -> list[QualityIssue]:
        return [i for i in self.all_issues if i.severity == "error"]

    @property
    def warnings(self) -> list[QualityIssue]:
        return [i for i in self.all_issues if i.severity == "warning"]

    @property
    def is_passing(self) -> bool:
        return len(self.errors) == 0 and self.overall_score >= 0.5

    def summary(self) -> str:
        lines = [
            f"═══ 5D Quality Report ═══",
            f"Overall Score: {self.overall_score:.2f}/1.00",
            f"",
            f"  Structure:  {self.structure.score:.2f}  ({len(self.structure.issues)} issues)",
            f"  Density:    {self.density.score:.2f}  ({len(self.density.issues)} issues)",
            f"  CRAP:       {self.crap.score:.2f}  ({len(self.crap.issues)} issues)",
            f"  Scene:      {self.scene.score:.2f}  ({len(self.scene.issues)} issues)",
            f"  Visual:     {self.visual.score:.2f}  ({len(self.visual.issues)} issues)",
            f"",
        ]
        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            for err in self.errors[:5]:
                lines.append(f"  {err}")
        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            for warn in self.warnings[:5]:
                lines.append(f"  {warn}")
        if not self.all_issues:
            lines.append("✅ No quality issues found")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 3),
            "is_passing": self.is_passing,
            "dimensions": {
                "structure": {
                    "score": round(self.structure.score, 3),
                    "issues": [str(i) for i in self.structure.issues],
                    "details": self.structure.details,
                },
                "density": {
                    "score": round(self.density.score, 3),
                    "issues": [str(i) for i in self.density.issues],
                    "details": self.density.details,
                },
                "crap": {
                    "score": round(self.crap.score, 3),
                    "issues": [str(i) for i in self.crap.issues],
                    "details": self.crap.details,
                },
                "scene": {
                    "score": round(self.scene.score, 3),
                    "issues": [str(i) for i in self.scene.issues],
                    "details": self.scene.details,
                },
                "visual": {
                    "score": round(self.visual.score, 3),
                    "issues": [str(i) for i in self.visual.issues],
                    "details": self.visual.details,
                },
            },
        }


# ─── Unified 5D Analyzer ────────────────────────────────────────────────

class QualityAnalyzer5D:
    """Unified 5D quality analyzer combining all dimensions."""

    def __init__(self):
        self.analyzer_4d = QualityAnalyzer4D()
        self.visual_checker = VisualQualityChecker()

    def analyze(
        self,
        slides: list[dict],
        context: dict | None = None,
        density_thresholds=None,
    ) -> QualityReport5D:
        """
        Run all five quality dimensions and produce a unified report.

        Args:
            slides: List of slide description dicts
            context: Optional context dict (document_type, book_title, etc.)
            density_thresholds: Optional custom density thresholds

        Returns:
            QualityReport5D with scores for all five dimensions
        """
        # Run 4D analysis
        report_4d = self.analyzer_4d.analyze(slides, context, density_thresholds)

        # Run visual analysis
        visual_score = self.visual_checker.validate(slides)

        return QualityReport5D(
            structure=report_4d.structure,
            density=report_4d.density,
            crap=report_4d.crap,
            scene=report_4d.scene,
            visual=visual_score,
        )


# ─── Convenience Function ─────────────────────────────────────────────────

def analyze_quality_5d(
    slides: list[dict],
    context: dict | None = None,
) -> QualityReport5D:
    """
    Convenience function to run 5D quality analysis.

    Args:
        slides: List of slide description dicts
        context: Optional context dict

    Returns:
        QualityReport5D
    """
    analyzer = QualityAnalyzer5D()
    return analyzer.analyze(slides, context)
