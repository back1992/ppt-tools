"""
4D Quality Framework for PPT slide descriptions.

Evaluates presentations across four dimensions:
1. Structure  - Logical slide order, progression, completeness
2. Density    - Content density (delegates to ContentDensityAnalyzer)
3. CRAP       - Design principles (Contrast, Repetition, Alignment, Proximity)
4. Scene      - Context/audience appropriateness

Each dimension produces a score (0.0-1.0) and a list of issues.
The overall QualityReport aggregates all four dimensions.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ─── Issue & Score Types ──────────────────────────────────────────────────

@dataclass
class QualityIssue:
    """A single quality issue in a specific dimension."""
    dimension: str  # "structure" | "density" | "crap" | "scene"
    severity: str   # "error" | "warning" | "info"
    code: str
    message: str
    slide_index: int = -1  # -1 = global issue

    def __str__(self):
        prefix = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.severity, "•")
        slide_info = f" (slide {self.slide_index})" if self.slide_index >= 0 else ""
        return f"{prefix} [{self.dimension}]{slide_info}: {self.message}"


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""
    dimension: str
    score: float  # 0.0-1.0
    issues: list[QualityIssue] = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class QualityReport:
    """Overall 4D quality report for a presentation."""
    structure: DimensionScore = field(default_factory=lambda: DimensionScore("structure", 1.0))
    density: DimensionScore = field(default_factory=lambda: DimensionScore("density", 1.0))
    crap: DimensionScore = field(default_factory=lambda: DimensionScore("crap", 1.0))
    scene: DimensionScore = field(default_factory=lambda: DimensionScore("scene", 1.0))

    @property
    def overall_score(self) -> float:
        """Weighted average of all four dimensions."""
        weights = {
            "structure": 0.25,
            "density": 0.30,
            "crap": 0.25,
            "scene": 0.20,
        }
        return (
            self.structure.score * weights["structure"]
            + self.density.score * weights["density"]
            + self.crap.score * weights["crap"]
            + self.scene.score * weights["scene"]
        )

    @property
    def all_issues(self) -> list[QualityIssue]:
        return (
            self.structure.issues
            + self.density.issues
            + self.crap.issues
            + self.scene.issues
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
            f"═══ 4D Quality Report ═══",
            f"Overall Score: {self.overall_score:.2f}/1.00",
            f"",
            f"  Structure:  {self.structure.score:.2f}  ({len(self.structure.issues)} issues)",
            f"  Density:    {self.density.score:.2f}  ({len(self.density.issues)} issues)",
            f"  CRAP:       {self.crap.score:.2f}  ({len(self.crap.issues)} issues)",
            f"  Scene:      {self.scene.score:.2f}  ({len(self.scene.issues)} issues)",
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
            },
            "total_issues": len(self.all_issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
        }


# ─── Structure Validator ──────────────────────────────────────────────────

class StructureValidator:
    """Validates logical slide structure and progression."""

    def validate(self, slides: list[dict]) -> DimensionScore:
        issues: list[QualityIssue] = []
        total = len(slides)

        if total < 3:
            issues.append(QualityIssue(
                dimension="structure", severity="warning", code="too_few_slides",
                message=f"Only {total} slides — consider adding more content",
            ))

        # Count slide types
        types = [s.get("type", "content") for s in slides]
        type_counts = {}
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1

        # Check for title slide
        if not any(t in ("title", "cover") for t in types):
            issues.append(QualityIssue(
                dimension="structure", severity="warning", code="no_title_slide",
                message="No title/cover slide found",
            ))

        # Check for outline/summary slide
        if not any(t in ("outline", "summary", "agenda") for t in types):
            issues.append(QualityIssue(
                dimension="structure", severity="info", code="no_outline",
                message="No outline/summary slide — helps audience follow structure",
            ))

        # Check for references/citations if content mentions sources
        has_citations = any(
            s.get("citations") or s.get("sources") or s.get("references")
            for s in slides
        )
        if has_citations and not any(t == "references" for t in types):
            issues.append(QualityIssue(
                dimension="structure", severity="warning", code="citations_no_references",
                message="Slides contain citations but no references slide",
            ))

        # Check slide order: title should be first
        if slides and types[0] not in ("title", "cover"):
            issues.append(QualityIssue(
                dimension="structure", severity="warning", code="title_not_first",
                message="First slide is not a title/cover slide",
            ))

        # Check for consecutive duplicate types (except content)
        for i in range(1, len(types)):
            if types[i] == types[i - 1] and types[i] != "content":
                issues.append(QualityIssue(
                    dimension="structure", severity="info", code="consecutive_same_type",
                    message=f"Consecutive {types[i]} slides at positions {i} and {i+1}",
                    slide_index=i,
                ))

        # Check variety — too many of the same type
        if total > 5:
            for slide_type, count in type_counts.items():
                if slide_type != "content" and count > total * 0.4:
                    issues.append(QualityIssue(
                        dimension="structure", severity="info", code="type_overuse",
                        message=f"Slide type '{slide_type}' used {count}/{total} times — consider more variety",
                    ))

        # Score: start at 1.0, deduct for issues
        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.2
            elif issue.severity == "warning":
                score -= 0.1
            else:
                score -= 0.03

        return DimensionScore(
            dimension="structure",
            score=max(0.0, score),
            issues=issues,
            details={
                "total_slides": total,
                "type_distribution": type_counts,
                "has_title": any(t in ("title", "cover") for t in types),
                "has_outline": any(t in ("outline", "summary") for t in types),
            },
        )


# ─── CRAP Checker ─────────────────────────────────────────────────────────

class CRAPChecker:
    """Validates CRAP design principles in slide descriptions.

    CRAP = Contrast, Repetition, Alignment, Proximity
    Applied to slide descriptions (not rendered slides).
    """

    def validate(self, slides: list[dict]) -> DimensionScore:
        issues: list[QualityIssue] = []

        # Contrast: check for visual emphasis differences
        issues.extend(self._check_contrast(slides))

        # Repetition: check for consistent patterns
        issues.extend(self._check_repetition(slides))

        # Alignment: check for consistent structure
        issues.extend(self._check_alignment(slides))

        # Proximity: check for grouped related content
        issues.extend(self._check_proximity(slides))

        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.15
            elif issue.severity == "warning":
                score -= 0.08
            else:
                score -= 0.02

        return DimensionScore(
            dimension="crap",
            score=max(0.0, score),
            issues=issues,
            details={
                "contrast_issues": len([i for i in issues if "contrast" in i.code]),
                "repetition_issues": len([i for i in issues if "repetition" in i.code]),
                "alignment_issues": len([i for i in issues if "alignment" in i.code]),
                "proximity_issues": len([i for i in issues if "proximity" in i.code]),
            },
        )

    def _check_contrast(self, slides: list[dict]) -> list[QualityIssue]:
        """Check that slides use visual contrast (headings vs body)."""
        issues = []
        for i, slide in enumerate(slides):
            slide_type = slide.get("type", "content")
            points = slide.get("points", [])

            # Content slides should have a title distinct from points
            title = slide.get("title", "")
            if slide_type == "content" and title and points:
                # Check if any point is same as title (no contrast)
                for point in points:
                    if isinstance(point, str) and point.strip() == title.strip():
                        issues.append(QualityIssue(
                            dimension="crap", severity="warning",
                            code="contrast_title_in_points",
                            message="Point text is identical to slide title",
                            slide_index=i,
                        ))

            # Definition slides should contrast term vs definition
            if slide_type == "definition":
                term = slide.get("term", "")
                definition = slide.get("definition", "")
                if term and definition and len(definition) < len(term) * 2:
                    issues.append(QualityIssue(
                        dimension="crap", severity="info",
                        code="contrast_short_definition",
                        message=f"Definition is very short compared to term — may lack visual contrast",
                        slide_index=i,
                    ))

        return issues

    def _check_repetition(self, slides: list[dict]) -> list[QualityIssue]:
        """Check for consistent patterns across slides."""
        issues = []

        content_slides = [s for s in slides if s.get("type") == "content"]
        if len(content_slides) < 3:
            return issues

        # Check bullet count consistency
        bullet_counts = [len(s.get("points", [])) for s in content_slides]
        if bullet_counts:
            avg_bullets = sum(bullet_counts) / len(bullet_counts)
            for i, slide in enumerate(slides):
                if slide.get("type") != "content":
                    continue
                count = len(slide.get("points", []))
                if count > 0 and abs(count - avg_bullets) > avg_bullets:
                    issues.append(QualityIssue(
                        dimension="crap", severity="info",
                        code="repetition_inconsistent_bullets",
                        message=f"Slide has {count} bullets (avg is {avg_bullets:.0f}) — inconsistent pattern",
                        slide_index=i,
                    ))

        return issues

    def _check_alignment(self, slides: list[dict]) -> list[QualityIssue]:
        """Check for structural alignment (consistent layout patterns)."""
        issues = []

        # Two-column slides should have balanced content
        for i, slide in enumerate(slides):
            if slide.get("type") == "comparison":
                left = slide.get("left_points", [])
                right = slide.get("right_points", [])
                if left and right and abs(len(left) - len(right)) > 2:
                    issues.append(QualityIssue(
                        dimension="crap", severity="warning",
                        code="alignment_unbalanced_columns",
                        message=f"Two-column slide has {len(left)} vs {len(right)} points — unbalanced",
                        slide_index=i,
                    ))

        return issues

    def _check_proximity(self, slides: list[dict]) -> list[QualityIssue]:
        """Check that related content is grouped together."""
        issues = []

        for i, slide in enumerate(slides):
            slide_type = slide.get("type", "content")
            points = slide.get("points", [])

            if slide_type == "content" and points:
                # Check if all points relate to the title topic
                # (heuristic: if points are very long, they may be unrelated paragraphs)
                long_points = [
                    p for p in points
                    if isinstance(p, str) and len(p) > 200
                ]
                if long_points:
                    issues.append(QualityIssue(
                        dimension="crap", severity="warning",
                        code="proximity_long_points",
                        message=f"Slide has {len(long_points)} very long point(s) — consider splitting into sub-points",
                        slide_index=i,
                    ))

        return issues


# ─── Scene Evaluator ──────────────────────────────────────────────────────

class SceneEvaluator:
    """Evaluates context/audience appropriateness."""

    def validate(self, slides: list[dict], context: dict | None = None) -> DimensionScore:
        issues: list[QualityIssue] = []
        context = context or {}

        total = len(slides)
        doc_type = context.get("document_type", "textbook")

        # Check slide count appropriateness for document type
        if doc_type == "textbook":
            if total > 25:
                issues.append(QualityIssue(
                    dimension="scene", severity="info", code="scene_too_many_slides",
                    message=f"{total} slides may be too many for a textbook chapter presentation",
                ))
            elif total < 5:
                issues.append(QualityIssue(
                    dimension="scene", severity="warning", code="scene_too_few_slides",
                    message=f"Only {total} slides — may not cover chapter content adequately",
                ))
        elif doc_type == "paper":
            if total > 20:
                issues.append(QualityIssue(
                    dimension="scene", severity="info", code="scene_too_many_slides",
                    message=f"{total} slides may be too many for a research paper presentation",
                ))

        # Check for academic-appropriate elements
        has_research_question = any(s.get("type") == "research_question" for s in slides)
        has_conclusions = any(s.get("type") in ("conclusions", "summary") for s in slides)

        if doc_type == "paper":
            if not has_research_question:
                issues.append(QualityIssue(
                    dimension="scene", severity="info", code="scene_no_research_question",
                    message="Paper presentation missing research question slide",
                ))
            if not has_conclusions:
                issues.append(QualityIssue(
                    dimension="scene", severity="warning", code="scene_no_conclusions",
                    message="Paper presentation missing conclusions slide",
                ))

        # Check title appropriateness
        for i, slide in enumerate(slides):
            title = slide.get("title", "")
            if title and len(title) > 100:
                issues.append(QualityIssue(
                    dimension="scene", severity="info", code="scene_long_title",
                    message=f"Slide title is {len(title)} chars — may be too long for presentation",
                    slide_index=i,
                ))

        # Check for appropriate language (no placeholder text)
        for i, slide in enumerate(slides):
            for key in ("title", "term", "definition", "quote"):
                text = slide.get(key, "")
                if "lorem ipsum" in text.lower() or "placeholder" in text.lower():
                    issues.append(QualityIssue(
                        dimension="scene", severity="error", code="scene_placeholder_text",
                        message=f"Slide contains placeholder text in '{key}'",
                        slide_index=i,
                    ))

        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.3
            elif issue.severity == "warning":
                score -= 0.1
            else:
                score -= 0.03

        return DimensionScore(
            dimension="scene",
            score=max(0.0, score),
            issues=issues,
            details={
                "document_type": doc_type,
                "total_slides": total,
                "has_research_question": has_research_question,
                "has_conclusions": has_conclusions,
            },
        )


# ─── Unified Analyzer ────────────────────────────────────────────────────

class QualityAnalyzer4D:
    """Unified 4D quality analyzer combining all dimensions."""

    def __init__(self):
        self.structure_validator = StructureValidator()
        self.crap_checker = CRAPChecker()
        self.scene_evaluator = SceneEvaluator()

    def analyze(
        self,
        slides: list[dict],
        context: dict | None = None,
        density_thresholds=None,
    ) -> QualityReport:
        """Run all four quality dimensions and produce a unified report.

        Args:
            slides: List of slide description dicts
            context: Optional context dict (document_type, book_title, etc.)
            density_thresholds: Optional custom density thresholds

        Returns:
            QualityReport with scores for all four dimensions
        """
        from .content_density import ContentDensityAnalyzer

        # 1. Structure
        structure_score = self.structure_validator.validate(slides)

        # 2. Density (delegate to existing analyzer)
        density_analyzer = ContentDensityAnalyzer(thresholds=density_thresholds)
        density_report = density_analyzer.analyze(slides)

        # Convert density issues to QualityIssue format
        density_issues = []
        for issue in density_report.issues:
            density_issues.append(QualityIssue(
                dimension="density",
                severity=issue.severity,
                code=issue.code,
                message=issue.message,
                slide_index=issue.slide_index,
            ))

        density_score = DimensionScore(
            dimension="density",
            score=density_report.overall_score,
            issues=density_issues,
            details={
                "content_slides": density_report.content_slides,
                "errors": len(density_report.errors),
                "warnings": len(density_report.warnings),
            },
        )

        # 3. CRAP
        crap_score = self.crap_checker.validate(slides)

        # 4. Scene
        scene_score = self.scene_evaluator.validate(slides, context)

        return QualityReport(
            structure=structure_score,
            density=density_score,
            crap=crap_score,
            scene=scene_score,
        )


# ─── Convenience Function ─────────────────────────────────────────────────

def analyze_quality_4d(
    slides: list[dict],
    context: dict | None = None,
) -> QualityReport:
    """Convenience function to run 4D quality analysis.

    Args:
        slides: List of slide description dicts
        context: Optional context dict

    Returns:
        QualityReport
    """
    analyzer = QualityAnalyzer4D()
    return analyzer.analyze(slides, context)
