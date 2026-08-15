"""Tests for 4D Quality Framework."""

import pytest
from ppt_quality_review.quality_4d import (
    StructureValidator,
    CRAPChecker,
    SceneEvaluator,
    QualityAnalyzer4D,
    QualityReport,
    QualityIssue,
    DimensionScore,
    analyze_quality_4d,
)


class TestStructureValidator:
    """Tests for StructureValidator."""

    def test_good_structure(self):
        """Well-structured presentation should score high."""
        slides = [
            {"type": "title", "title": "Introduction to AI"},
            {"type": "outline", "title": "Overview", "items": ["A", "B", "C"]},
            {"type": "content", "title": "Background", "points": ["P1", "P2", "P3"]},
            {"type": "content", "title": "Methods", "points": ["P1", "P2"]},
            {"type": "definition", "term": "AI", "definition": "Artificial intelligence"},
            {"type": "summary", "title": "Summary", "items": ["A", "B"]},
        ]
        validator = StructureValidator()
        score = validator.validate(slides)
        assert score.score >= 0.8
        assert score.dimension == "structure"

    def test_no_title_slide(self):
        """Missing title slide should produce warning."""
        slides = [
            {"type": "content", "title": "Background", "points": ["P1", "P2"]},
            {"type": "content", "title": "Methods", "points": ["P1", "P2"]},
        ]
        validator = StructureValidator()
        score = validator.validate(slides)
        assert any("no_title_slide" in i.code for i in score.issues)

    def test_title_not_first(self):
        """Title slide not being first should warn."""
        slides = [
            {"type": "content", "title": "Background", "points": ["P1"]},
            {"type": "title", "title": "My Presentation"},
            {"type": "content", "title": "Methods", "points": ["P1"]},
        ]
        validator = StructureValidator()
        score = validator.validate(slides)
        assert any("title_not_first" in i.code for i in score.issues)

    def test_too_few_slides(self):
        """Very few slides should produce warning."""
        slides = [
            {"type": "title", "title": "Hi"},
            {"type": "content", "title": "Content", "points": ["P1"]},
        ]
        validator = StructureValidator()
        score = validator.validate(slides)
        assert any("too_few_slides" in i.code for i in score.issues)


class TestCRAPChecker:
    """Tests for CRAPChecker."""

    def test_no_issues(self):
        """Well-designed slides should have no CRAP issues."""
        slides = [
            {"type": "title", "title": "Introduction"},
            {"type": "content", "title": "Background", "points": ["Point 1", "Point 2"]},
            {"type": "content", "title": "Methods", "points": ["Point 1", "Point 2"]},
        ]
        checker = CRAPChecker()
        score = checker.validate(slides)
        assert score.score >= 0.9

    def test_title_in_points(self):
        """Point identical to title should flag contrast issue."""
        slides = [
            {"type": "content", "title": "Background", "points": ["Background", "Point 2"]},
        ]
        checker = CRAPChecker()
        score = checker.validate(slides)
        assert any("contrast_title_in_points" in i.code for i in score.issues)

    def test_unbalanced_comparison(self):
        """Unbalanced two-column slide should flag alignment issue."""
        slides = [
            {
                "type": "comparison",
                "title": "Pros vs Cons",
                "left_points": ["P1", "P2", "P3", "P4", "P5"],
                "right_points": ["P1"],
            },
        ]
        checker = CRAPChecker()
        score = checker.validate(slides)
        assert any("alignment_unbalanced" in i.code for i in score.issues)

    def test_long_points(self):
        """Very long points should flag proximity issue."""
        long_text = "This is a very long point that contains way too much text for a single slide bullet and should be split into sub-points for better readability and visual proximity. " * 3
        slides = [
            {"type": "content", "title": "Details", "points": [long_text]},
        ]
        checker = CRAPChecker()
        score = checker.validate(slides)
        assert any("proximity_long_points" in i.code for i in score.issues)


class TestSceneEvaluator:
    """Tests for SceneEvaluator."""

    def test_good_textbook_scene(self):
        """Well-structured textbook presentation should score high."""
        slides = [
            {"type": "title", "title": "Chapter 1"},
            {"type": "content", "title": "Section 1", "points": ["P1", "P2"]},
            {"type": "content", "title": "Section 2", "points": ["P1", "P2"]},
            {"type": "summary", "title": "Summary", "items": ["A"]},
        ]
        evaluator = SceneEvaluator()
        score = evaluator.validate(slides, {"document_type": "textbook"})
        assert score.score >= 0.8

    def test_placeholder_text(self):
        """Placeholder text should be an error."""
        slides = [
            {"type": "content", "title": "Lorem ipsum dolor", "points": ["P1"]},
        ]
        evaluator = SceneEvaluator()
        score = evaluator.validate(slides)
        assert any("placeholder" in i.code for i in score.issues)

    def test_paper_missing_conclusions(self):
        """Paper without conclusions should warn."""
        slides = [
            {"type": "title", "title": "Research Paper"},
            {"type": "content", "title": "Methods", "points": ["P1"]},
        ]
        evaluator = SceneEvaluator()
        score = evaluator.validate(slides, {"document_type": "paper"})
        assert any("scene_no_conclusions" in i.code for i in score.issues)


class TestQualityReport:
    """Tests for QualityReport."""

    def test_overall_score_weighted(self):
        """Overall score should be weighted average."""
        report = QualityReport(
            structure=DimensionScore("structure", 1.0),
            density=DimensionScore("density", 0.8),
            crap=DimensionScore("crap", 1.0),
            scene=DimensionScore("scene", 0.6),
        )
        # 1.0*0.25 + 0.8*0.30 + 1.0*0.25 + 0.6*0.20 = 0.25 + 0.24 + 0.25 + 0.12 = 0.86
        assert abs(report.overall_score - 0.86) < 0.01

    def test_to_dict(self):
        """to_dict should produce a serializable dict."""
        report = QualityReport()
        d = report.to_dict()
        assert "overall_score" in d
        assert "dimensions" in d
        assert "structure" in d["dimensions"]
        assert "density" in d["dimensions"]
        assert "crap" in d["dimensions"]
        assert "scene" in d["dimensions"]

    def test_summary(self):
        """summary() should produce readable output."""
        report = QualityReport(
            structure=DimensionScore("structure", 0.9, [
                QualityIssue("structure", "info", "test", "Test issue")
            ]),
        )
        text = report.summary()
        assert "4D Quality Report" in text
        assert "Structure" in text


class TestQualityAnalyzer4D:
    """Integration tests for the unified analyzer."""

    def test_full_analysis(self):
        """Should run all four dimensions."""
        slides = [
            {"type": "title", "title": "Introduction"},
            {"type": "outline", "title": "Overview", "items": ["A", "B"]},
            {"type": "content", "title": "Background", "points": ["P1", "P2", "P3"]},
            {"type": "content", "title": "Methods", "points": ["P1", "P2"]},
            {"type": "definition", "term": "AI", "definition": "Artificial intelligence is the simulation of human intelligence."},
            {"type": "summary", "title": "Summary", "items": ["A", "B"]},
        ]
        analyzer = QualityAnalyzer4D()
        report = analyzer.analyze(slides)
        assert isinstance(report, QualityReport)
        assert 0.0 <= report.overall_score <= 1.0
        assert report.structure.score > 0
        assert report.density.score > 0
        assert report.crap.score > 0
        assert report.scene.score > 0

    def test_convenience_function(self):
        """analyze_quality_4d should work as convenience function."""
        slides = [
            {"type": "title", "title": "Test"},
            {"type": "content", "title": "Content", "points": ["P1", "P2"]},
        ]
        report = analyze_quality_4d(slides)
        assert isinstance(report, QualityReport)
