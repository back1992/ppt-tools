"""Tests for content density quality control."""

import pytest
from ppt_quality_review.content_density import (
    ContentDensityAnalyzer,
    Thresholds,
    DensityReport,
    SlideDensityIssue,
    SlideDensityScore,
    analyze_content_density,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def analyzer():
    return ContentDensityAnalyzer()


@pytest.fixture
def custom_thresholds():
    return Thresholds(
        max_bullets=4,
        max_words_per_bullet=15,
        max_total_words=40,
    )


def _make_slides(*slide_dicts):
    """Helper to create a list of slide dicts."""
    return list(slide_dicts)


# ─── Content Slide Tests (Latin) ──────────────────────────────────────────


class TestContentSlides:
    """Tests for content slide density analysis."""

    def test_good_content_slide(self, analyzer):
        """A well-balanced content slide should have no issues."""
        slides = _make_slides({
            "type": "content",
            "title": "Communication Models",
            "points": [
                "Shannon-Weaver model describes linear transmission",
                "Transactional model emphasizes feedback loops",
                "Semiotic approach focuses on meaning construction",
            ],
        })

        report = analyzer.analyze(slides)

        assert report.total_slides == 1
        assert report.content_slides == 1
        assert report.is_passing
        assert len(report.errors) == 0

    def test_too_many_bullets(self, analyzer):
        """Slides with too many bullets should report an error."""
        slides = _make_slides({
            "type": "content",
            "title": "Key Concepts",
            "points": [f"Point {i}" for i in range(10)],
        })

        report = analyzer.analyze(slides)

        assert not report.is_passing
        assert any(i.code == "too_many_bullets" for i in report.errors)

    def test_too_few_bullets(self, analyzer):
        """A slide with only 1 bullet should warn about sparsity."""
        slides = _make_slides({
            "type": "content",
            "title": "Single Point",
            "points": ["Only one point here"],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "too_few_bullets" for i in report.warnings)

    def test_bullet_too_long(self, analyzer):
        """Bullets exceeding the word limit should be flagged."""
        long_bullet = " ".join(["word"] * 25)  # 25 words > 20 max
        slides = _make_slides({
            "type": "content",
            "title": "Verbose Slide",
            "points": [
                "Short point",
                long_bullet,
                "Another short point",
            ],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "bullet_too_long" for i in report.errors)

    def test_bullet_verbose_warning(self, analyzer):
        """Bullets near the limit should get warnings, not errors."""
        verbose_bullet = " ".join(["word"] * 17)  # 17 words > 15 warn
        slides = _make_slides({
            "type": "content",
            "title": "Verbose Slide",
            "points": [
                "Short point",
                verbose_bullet,
                "Another short point",
            ],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "bullet_verbose" for i in report.warnings)
        assert not any(i.code == "bullet_too_long" for i in report.errors)

    def test_slide_too_dense(self, analyzer):
        """Total word count exceeding limit should be an error."""
        # 15 words × 4 bullets = 60 words > 60 max (exactly at limit)
        # Need more than 60
        slides = _make_slides({
            "type": "content",
            "title": "Dense Slide",
            "points": [
                " ".join(["word"] * 18),
                " ".join(["word"] * 18),
                " ".join(["word"] * 18),
                " ".join(["word"] * 18),
            ],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "slide_too_dense" for i in report.errors)

    def test_slide_too_sparse(self, analyzer):
        """A content slide with very little text should warn."""
        slides = _make_slides({
            "type": "content",
            "title": "Sparse Slide",
            "points": ["Hi", "Yo"],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "slide_too_sparse" for i in report.warnings)

    def test_empty_points_list(self, analyzer):
        """Content slide with empty points should not crash."""
        slides = _make_slides({
            "type": "content",
            "title": "Empty Content",
            "points": [],
        })

        report = analyzer.analyze(slides)

        # Should have warning about too few bullets
        assert any(i.code == "too_few_bullets" for i in report.warnings)


# ─── Content Slide Tests (CJK) ────────────────────────────────────────────


class TestCJKContentSlides:
    """Tests for CJK content slide density analysis."""

    def test_good_cjk_content_slide(self, analyzer):
        """A well-balanced CJK content slide should have no issues."""
        slides = _make_slides({
            "type": "content",
            "title": "传播模式分析",
            "points": [
                "香农-韦弗模式描述线性传播过程",
                "奥斯古德-施拉姆模式强调循环反馈",
                "德弗勒模式包含噪声因素的影响",
            ],
        })

        report = analyzer.analyze(slides)

        assert report.is_passing
        assert len(report.errors) == 0

    def test_cjk_bullet_too_long(self, analyzer):
        """CJK bullets exceeding character limit should be flagged."""
        # 45 Chinese chars > 40 max
        long_bullet = "传播学" * 15  # 45 chars
        slides = _make_slides({
            "type": "content",
            "title": "冗长的幻灯片",
            "points": [
                "简短要点",
                long_bullet,
                "另一个简短要点",
            ],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "bullet_too_long" for i in report.errors)

    def test_cjk_slide_too_dense(self, analyzer):
        """Total CJK character count exceeding limit should be an error."""
        slides = _make_slides({
            "type": "content",
            "title": "密度过高",
            "points": [
                "这是一段很长的中文内容用来测试幻灯片密度控制功能",
                "这是另一段很长的内容需要检测字符数量",
                "还有更多的文字需要被分析和评估",
                "最后一段也很长的中文文本内容",
            ],
        })

        report = analyzer.analyze(slides)

        # Should have density issues due to high char count
        assert len(report.issues) > 0


# ─── Definition Slide Tests ───────────────────────────────────────────────


class TestDefinitionSlides:
    """Tests for definition slide density analysis."""

    def test_good_definition(self, analyzer):
        """A properly-sized definition should pass."""
        slides = _make_slides({
            "type": "definition",
            "term": "Communication",
            "definition": "The process of exchanging information and meaning "
                          "between individuals through symbols and signs.",
        })

        report = analyzer.analyze(slides)

        assert report.is_passing
        assert len(report.errors) == 0

    def test_definition_too_long(self, analyzer):
        """Overly verbose definitions should be flagged."""
        long_def = " ".join(["word"] * 100)
        slides = _make_slides({
            "type": "definition",
            "term": "Communication",
            "definition": long_def,
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "definition_too_long" for i in report.errors)

    def test_definition_too_short(self, analyzer):
        """Very short definitions should get a warning."""
        slides = _make_slides({
            "type": "definition",
            "term": "Communication",
            "definition": "Info exchange.",
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "definition_too_short" for i in report.warnings)

    def test_cjk_definition(self, analyzer):
        """CJK definition should use character-based thresholds."""
        slides = _make_slides({
            "type": "definition",
            "term": "传播",
            "definition": "信息在发送者和接收者之间传递和交流的过程。",
        })

        report = analyzer.analyze(slides)

        assert report.is_passing

    def test_cjk_definition_too_long(self, analyzer):
        """Very long CJK definitions should be flagged."""
        long_def = "传播学" * 60  # 180 chars > 150 max
        slides = _make_slides({
            "type": "definition",
            "term": "传播学",
            "definition": long_def,
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "definition_too_long" for i in report.errors)


# ─── Quote Slide Tests ────────────────────────────────────────────────────


class TestQuoteSlides:
    """Tests for quote slide density analysis."""

    def test_good_quote(self, analyzer):
        """A concise quote should pass."""
        slides = _make_slides({
            "type": "quote",
            "quote": "Communication is the process of sharing meaning.",
            "attribution": "Schramm, 1954",
        })

        report = analyzer.analyze(slides)

        assert report.is_passing

    def test_quote_too_long(self, analyzer):
        """Overly long quotes should get a warning."""
        long_quote = " ".join(["word"] * 60)  # 60 words > 50 max
        slides = _make_slides({
            "type": "quote",
            "quote": long_quote,
            "attribution": "Someone",
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "quote_too_long" for i in report.warnings)


# ─── Outline / Summary Slide Tests ────────────────────────────────────────


class TestListSlides:
    """Tests for outline and summary slide density."""

    def test_good_outline(self, analyzer):
        """A normal outline should pass."""
        slides = _make_slides({
            "type": "outline",
            "title": "Chapter Outline",
            "items": ["Introduction", "Methods", "Results", "Discussion"],
        })

        report = analyzer.analyze(slides)

        assert report.is_passing

    def test_too_many_items(self, analyzer):
        """Outlines with too many items should be flagged."""
        slides = _make_slides({
            "type": "outline",
            "title": "Overloaded Outline",
            "items": [f"Section {i}" for i in range(12)],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "too_many_items" for i in report.errors)

    def test_too_few_items(self, analyzer):
        """Outlines with very few items should warn."""
        slides = _make_slides({
            "type": "summary",
            "title": "Summary",
            "items": ["Only one"],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "too_few_items" for i in report.warnings)


# ─── Comparison Slide Tests ───────────────────────────────────────────────


class TestComparisonSlides:
    """Tests for comparison slide density analysis."""

    def test_balanced_comparison(self, analyzer):
        """A balanced comparison slide should pass."""
        slides = _make_slides({
            "type": "comparison",
            "title": "Linear vs. Transactional",
            "left_title": "Linear Model",
            "left_points": ["One-way", "No feedback"],
            "right_title": "Transactional Model",
            "right_points": ["Two-way", "Continuous feedback"],
        })

        report = analyzer.analyze(slides)

        assert report.is_passing

    def test_unbalanced_comparison(self, analyzer):
        """Heavily unbalanced sides should warn."""
        slides = _make_slides({
            "type": "comparison",
            "title": "Unbalanced",
            "left_title": "Left",
            "left_points": ["One point"],
            "right_title": "Right",
            "right_points": [f"Point {i}" for i in range(4)],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "unbalanced_sides" for i in report.warnings)

    def test_too_many_bullets_per_side(self, analyzer):
        """Sides with too many bullets should be flagged."""
        slides = _make_slides({
            "type": "comparison",
            "title": "Overloaded Comparison",
            "left_title": "Left",
            "left_points": [f"Point {i}" for i in range(6)],
            "right_title": "Right",
            "right_points": [f"Point {i}" for i in range(2)],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "left_too_many_bullets" for i in report.errors)


# ─── Image Slide Tests ────────────────────────────────────────────────────


class TestImageSlides:
    """Tests for image slide density analysis."""

    def test_good_image_slide(self, analyzer):
        """An image slide with few context points should pass."""
        slides = _make_slides({
            "type": "image",
            "title": "Communication Flow Diagram",
            "context_points": ["Shows sender-receiver model", "Illustrates feedback loop"],
        })

        report = analyzer.analyze(slides)

        assert report.is_passing

    def test_image_too_many_points(self, analyzer):
        """Image slides with too many points should warn."""
        slides = _make_slides({
            "type": "image",
            "title": "Overloaded Image",
            "context_points": [f"Point {i}" for i in range(7)],
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "image_too_many_points" for i in report.warnings)


# ─── Distribution Tests ───────────────────────────────────────────────────


class TestDistribution:
    """Tests for overall presentation distribution analysis."""

    def test_too_many_slides(self, analyzer):
        """Presentations exceeding max slides should be flagged."""
        slides = [
            {"type": "content", "title": f"Slide {i}", "points": ["A", "B", "C"]}
            for i in range(30)
        ]

        report = analyzer.analyze(slides)

        assert any(i.code == "too_many_slides" for i in report.errors)

    def test_too_few_slides(self, analyzer):
        """Very short presentations should warn."""
        slides = _make_slides(
            {"type": "title", "title": "Title"},
            {"type": "content", "title": "Only Content", "points": ["A", "B"]},
            {"type": "summary", "title": "Summary", "items": ["A"]},
        )

        report = analyzer.analyze(slides)

        assert any(i.code == "too_few_slides" for i in report.warnings)

    def test_high_content_ratio(self, analyzer):
        """Too many content slides relative to other types should warn."""
        slides = (
            [{"type": "content", "title": f"C{i}", "points": ["A", "B", "C"]} for i in range(15)]
            + [{"type": "title", "title": "Title"}]
            + [{"type": "summary", "title": "Summary", "items": ["A", "B"]}]
        )

        report = analyzer.analyze(slides)

        assert any(i.code == "high_content_ratio" for i in report.warnings)


# ─── Custom Thresholds Tests ─────────────────────────────────────────────


class TestCustomThresholds:
    """Tests for configurable thresholds."""

    def test_custom_max_bullets(self):
        """Custom thresholds should be respected."""
        custom = Thresholds(max_bullets=3, min_bullets=1)
        analyzer = ContentDensityAnalyzer(thresholds=custom)

        slides = _make_slides({
            "type": "content",
            "title": "Test",
            "points": ["A", "B", "C", "D"],  # 4 > custom max of 3
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "too_many_bullets" for i in report.errors)

    def test_custom_max_words(self):
        """Custom word limit should be applied."""
        custom = Thresholds(max_words_per_bullet=10)
        analyzer = ContentDensityAnalyzer(thresholds=custom)

        slides = _make_slides({
            "type": "content",
            "title": "Test",
            "points": ["A " * 12, "B", "C"],  # first point = 12 words > 10
        })

        report = analyzer.analyze(slides)

        assert any(i.code == "bullet_too_long" for i in report.errors)


# ─── Scoring Tests ────────────────────────────────────────────────────────


class TestScoring:
    """Tests for density scoring system."""

    def test_perfect_slide_score(self, analyzer):
        """A slide with no per-slide issues should score 1.0 on that slide."""
        slides = _make_slides({
            "type": "content",
            "title": "Perfect",
            "points": ["Good point one", "Good point two", "Good point three"],
        })

        report = analyzer.analyze(slides)

        # Individual slide should score 1.0
        assert report.slide_scores[0].score == 1.0
        # Overall may be reduced by distribution warnings on small presentations
        assert report.overall_score >= 0.9

    def test_penalty_reduces_score(self, analyzer):
        """Issues should reduce the overall score."""
        slides = _make_slides({
            "type": "content",
            "title": "Problem Slide",
            "points": [f"Point {i} " + "word " * 20 for i in range(10)],
        })

        report = analyzer.analyze(slides)

        assert report.overall_score < 1.0
        assert report.overall_score >= 0.0

    def test_empty_presentation_score(self, analyzer):
        """Empty presentation should score 1.0 (no slides = no issues)."""
        report = analyzer.analyze([])

        assert report.overall_score == 1.0
        assert report.total_slides == 0


# ─── Report Tests ─────────────────────────────────────────────────────────


class TestReport:
    """Tests for DensityReport data class."""

    def test_report_summary_no_issues(self, analyzer):
        """Summary should indicate no issues when a well-structured presentation is clean."""
        slides = _make_slides(
            {"type": "title", "title": "Chapter 1"},
            {"type": "outline", "title": "Overview", "items": ["A", "B", "C"]},
            {"type": "content", "title": "Section A", "points": ["Good point", "Another point", "Third point"]},
            {"type": "definition", "term": "Key Term", "definition": "A clear and concise definition that provides sufficient detail for understanding."},
            {"type": "content", "title": "Section B", "points": ["First point", "Second point"]},
            {"type": "summary", "title": "Summary", "items": ["A", "B"]},
        )

        report = analyzer.analyze(slides)
        summary = report.summary()

        assert "No density issues" in summary

    def test_report_summary_with_issues(self, analyzer):
        """Summary should list errors and warnings."""
        slides = _make_slides({
            "type": "content",
            "title": "Bad Slide",
            "points": [f"P{i}" for i in range(10)],
        })

        report = analyzer.analyze(slides)
        summary = report.summary()

        assert "error" in summary.lower() or "warning" in summary.lower()

    def test_errors_property(self, analyzer):
        """errors property should only return error-severity issues."""
        slides = _make_slides({
            "type": "content",
            "title": "Mixed",
            "points": [f"Point {i}" for i in range(10)],
        })

        report = analyzer.analyze(slides)

        for err in report.errors:
            assert err.severity == "error"

    def test_warnings_property(self, analyzer):
        """warnings property should only return warning-severity issues."""
        slides = _make_slides({
            "type": "content",
            "title": "Sparse",
            "points": ["One"],
        })

        report = analyzer.analyze(slides)

        for warn in report.warnings:
            assert warn.severity == "warning"


# ─── Convenience Function Tests ───────────────────────────────────────────


class TestConvenienceFunction:
    """Tests for the analyze_content_density() convenience function."""

    def test_basic_usage(self):
        """Should work as a simple function call."""
        slides = _make_slides({
            "type": "content",
            "title": "Test",
            "points": ["A", "B", "C"],
        })

        report = analyze_content_density(slides)

        assert isinstance(report, DensityReport)
        assert report.total_slides == 1

    def test_with_custom_thresholds(self):
        """Should accept custom thresholds."""
        slides = _make_slides({
            "type": "content",
            "title": "Test",
            "points": ["A", "B", "C", "D"],
        })

        custom = Thresholds(max_bullets=3)
        report = analyze_content_density(slides, thresholds=custom)

        assert any(i.code == "too_many_bullets" for i in report.issues)


# ─── Edge Cases ───────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge cases and robustness."""

    def test_missing_type_field(self, analyzer):
        """Slides without a type field should be handled gracefully."""
        slides = _make_slides({"title": "No Type"})

        report = analyzer.analyze(slides)

        # Should not crash
        assert report.total_slides == 1

    def test_missing_points_field(self, analyzer):
        """Content slides without points should not crash."""
        slides = _make_slides({"type": "content", "title": "No Points"})

        report = analyzer.analyze(slides)

        assert any(i.code == "too_few_bullets" for i in report.warnings)

    def test_non_list_points(self, analyzer):
        """Points as a non-list should be handled."""
        slides = _make_slides({
            "type": "content",
            "title": "String Points",
            "points": "not a list",
        })

        report = analyzer.analyze(slides)

        # Should treat as empty
        assert any(i.code == "too_few_bullets" for i in report.warnings)

    def test_mixed_language_slides(self, analyzer):
        """A presentation mixing CJK and Latin slides should work."""
        slides = _make_slides(
            {"type": "content", "title": "English Slide", "points": ["Point A", "Point B", "Point C"]},
            {"type": "content", "title": "中文幻灯片", "points": ["要点一", "要点二", "要点三"]},
            {"type": "definition", "term": "Term", "definition": "A definition."},
        )

        report = analyzer.analyze(slides)

        assert report.total_slides == 3
        # Each slide should be scored independently
        assert len(report.slide_scores) == 3

    def test_slide_issue_str(self, analyzer):
        """SlideDensityIssue.__str__ should produce readable output."""
        issue = SlideDensityIssue(
            slide_index=2,
            slide_type="content",
            slide_title="Test Title",
            severity="error",
            code="too_many_bullets",
            message="8 bullets — maximum 6",
        )

        s = str(issue)
        assert "Slide 2" in s
        assert "content" in s
        assert "8 bullets" in s

    def test_mixed_slide_types(self, analyzer):
        """A realistic mix of slide types should be analyzable."""
        slides = _make_slides(
            {"type": "title", "title": "Chapter 1", "subtitle": "Book"},
            {"type": "outline", "title": "Overview", "items": ["A", "B", "C"]},
            {"type": "content", "title": "Section A", "points": ["P1", "P2", "P3"]},
            {"type": "definition", "term": "Key", "definition": "Important definition here."},
            {"type": "content", "title": "Section B", "points": ["P1", "P2", "P3", "P4"]},
            {"type": "comparison", "title": "Compare", "left_title": "A",
             "left_points": ["X"], "right_title": "B", "right_points": ["Y"]},
            {"type": "summary", "title": "Summary", "items": ["A", "B"]},
        )

        report = analyzer.analyze(slides)

        assert report.total_slides == 7
        assert report.is_passing  # well-structured presentation
