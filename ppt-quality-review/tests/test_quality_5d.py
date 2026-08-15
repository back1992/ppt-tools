"""Tests for 5D quality framework (Visual dimension)."""

import sys

import pytest

from ppt_quality_review.quality_5d import (
    VisualQualityChecker,
    QualityReport5D,
    QualityAnalyzer5D,
    analyze_quality_5d,
)
from ppt_quality_review.quality_4d import DimensionScore, QualityIssue


class TestVisualQualityChecker:
    """Test suite for VisualQualityChecker."""

    def setup_method(self):
        self.checker = VisualQualityChecker()

    def test_empty_slides_returns_perfect_score(self):
        """Empty presentation should have perfect visual score."""
        score = self.checker.validate([])
        assert score.score == 1.0
        assert score.dimension == "visual"
        assert len(score.issues) == 0

    def test_no_images_triggers_warnings(self):
        """Presentation with no images should trigger warnings."""
        slides = [
            {"type": "content", "title": "Slide 1", "points": ["point 1"]},
            {"type": "content", "title": "Slide 2", "points": ["point 2"]},
            {"type": "content", "title": "Slide 3", "points": ["point 3"]},
        ]
        score = self.checker.validate(slides)
        assert score.score < 1.0
        assert any(i.code == "too_few_images" for i in score.issues)
        assert any(i.code == "low_image_ratio" for i in score.issues)

    def test_sufficient_images_no_warnings(self):
        """Presentation with enough images should not trigger warnings."""
        slides = [
            {"type": "content", "title": "Slide 1", "image_path": "/img1.png"},
            {"type": "content", "title": "Slide 2", "image_path": "/img2.png"},
            {"type": "content", "title": "Slide 3", "points": ["point 3"]},
        ]
        score = self.checker.validate(slides)
        # 2/3 = 67% > 30% threshold
        assert not any(i.code == "low_image_ratio" for i in score.issues)
        assert not any(i.code == "too_few_images" for i in score.issues)

    def test_figure_type_counts_as_image(self):
        """Figure slides should count as having images."""
        slides = [
            {"type": "figure", "title": "Diagram", "image_path": "/img.png"},
            {"type": "content", "title": "Slide 2", "points": ["point 2"]},
        ]
        score = self.checker.validate(slides)
        assert score.details["slides_with_images"] == 1

    def test_text_heavy_slide_flagged(self):
        """Content slides with lots of text but no image should be flagged."""
        slides = [
            {
                "type": "content",
                "title": "Dense Slide",
                "points": ["A" * 100, "B" * 100, "C" * 100],  # 300+ chars
            },
        ]
        score = self.checker.validate(slides)
        assert any(i.code == "text_heavy_no_image" for i in score.issues)

    def test_text_heavy_with_image_not_flagged(self):
        """Content slides with images should not be flagged as text-heavy."""
        slides = [
            {
                "type": "content",
                "title": "Dense Slide",
                "points": ["A" * 100, "B" * 100],
                "image_path": "/img.png",
            },
        ]
        score = self.checker.validate(slides)
        assert not any(i.code == "text_heavy_no_image" for i in score.issues)

    def test_details_populated(self):
        """Details dict should be populated with image stats."""
        slides = [
            {"type": "content", "title": "S1", "image_path": "/img1.png"},
            {"type": "content", "title": "S2", "points": ["p2"]},
        ]
        score = self.checker.validate(slides)
        assert "slides_with_images" in score.details
        assert "total_slides" in score.details
        assert "image_ratio" in score.details
        assert score.details["slides_with_images"] == 1
        assert score.details["total_slides"] == 2


def test_visual_check_skips_rhythm_when_ppt_generator_absent(monkeypatch):
    """Standalone consumers without ppt_generator must not crash."""
    monkeypatch.delitem(sys.modules, "ppt_generator.theme_rhythm", raising=False)
    monkeypatch.setitem(sys.modules, "ppt_generator", None)
    report = analyze_quality_5d(
        [{"points": ["Hello world"], "image_path": "img.png"}]
    )
    assert report.visual.details["rhythm"] == {}


class TestQualityReport5D:
    """Test suite for QualityReport5D."""

    def test_overall_score_includes_visual(self):
        """Overall score should include visual dimension."""
        report = QualityReport5D(
            structure=DimensionScore("structure", 1.0),
            density=DimensionScore("density", 1.0),
            crap=DimensionScore("crap", 1.0),
            scene=DimensionScore("scene", 1.0),
            visual=DimensionScore("visual", 0.5),
        )
        # Weights: 0.20 + 0.25 + 0.20 + 0.15 + 0.20*0.5 = 0.90
        assert report.overall_score == pytest.approx(0.90, abs=0.01)

    def test_all_issues_includes_visual(self):
        """all_issues should include visual issues."""
        visual_issue = QualityIssue(
            dimension="visual",
            severity="warning",
            code="test",
            message="Test issue",
        )
        report = QualityReport5D(
            visual=DimensionScore("visual", 0.8, issues=[visual_issue]),
        )
        assert visual_issue in report.all_issues

    def test_summary_includes_visual_dimension(self):
        """Summary should include visual dimension."""
        report = QualityReport5D()
        summary = report.summary()
        assert "Visual:" in summary

    def test_to_dict_includes_visual(self):
        """to_dict should include visual dimension."""
        report = QualityReport5D()
        data = report.to_dict()
        assert "visual" in data["dimensions"]


class TestQualityAnalyzer5D:
    """Test suite for QualityAnalyzer5D."""

    def test_analyze_returns_5d_report(self):
        """analyze() should return QualityReport5D."""
        analyzer = QualityAnalyzer5D()
        slides = [
            {"type": "title", "title": "Title"},
            {"type": "content", "title": "Content", "points": ["p1"]},
        ]
        report = analyzer.analyze(slides)
        assert isinstance(report, QualityReport5D)
        assert hasattr(report, "visual")

    def test_analyze_includes_all_dimensions(self):
        """Report should have all 5 dimensions."""
        analyzer = QualityAnalyzer5D()
        slides = [
            {"type": "title", "title": "Title"},
            {"type": "content", "title": "Content", "points": ["p1", "p2"]},
        ]
        report = analyzer.analyze(slides)
        assert report.structure.dimension == "structure"
        assert report.density.dimension == "density"
        assert report.crap.dimension == "crap"
        assert report.scene.dimension == "scene"
        assert report.visual.dimension == "visual"


class TestConvenienceFunction:
    """Test suite for analyze_quality_5d convenience function."""

    def test_analyze_quality_5d_works(self):
        """Convenience function should work."""
        slides = [
            {"type": "title", "title": "Title"},
            {"type": "content", "title": "Content", "points": ["p1"]},
        ]
        report = analyze_quality_5d(slides)
        assert isinstance(report, QualityReport5D)
