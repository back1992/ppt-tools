"""Tests for image density analysis."""

import pytest

from ppt_quality_review.image_density import ImageDensityAnalyzer, ImageDensityReport


class TestImageDensityAnalyzer:
    """Test suite for ImageDensityAnalyzer."""

    def setup_method(self):
        self.analyzer = ImageDensityAnalyzer()

    def test_zero_slides_returns_no_deficit(self):
        """Zero slides should not trigger AI generation."""
        report = self.analyzer.analyze(slide_count=0, image_count=0)
        assert report.needs_ai_images is False
        assert report.deficit == 0
        assert report.total_slides == 0

    def test_negative_slides_returns_no_deficit(self):
        """Negative slide count should be handled gracefully."""
        report = self.analyzer.analyze(slide_count=-5, image_count=0)
        assert report.needs_ai_images is False
        assert report.deficit == 0

    def test_no_images_triggers_deficit(self):
        """Presentation with no images should need AI images."""
        report = self.analyzer.analyze(slide_count=10, image_count=0)
        assert report.needs_ai_images is True
        # target = max(2, int(10 * 0.3)) = max(2, 3) = 3
        assert report.deficit == 3
        assert report.image_to_slide_ratio == 0.0

    def test_few_images_triggers_deficit(self):
        """Presentation with too few images should need more."""
        report = self.analyzer.analyze(slide_count=10, image_count=1)
        assert report.needs_ai_images is True
        # target = 3, deficit = 3 - 1 = 2
        assert report.deficit == 2

    def test_sufficient_images_no_deficit(self):
        """Presentation with enough images should not need more."""
        report = self.analyzer.analyze(slide_count=10, image_count=5)
        assert report.needs_ai_images is False
        assert report.deficit == 0
        assert report.image_to_slide_ratio == 0.5

    def test_exact_threshold_no_deficit(self):
        """Presentation at exactly the threshold should not need more."""
        # 10 slides, target = max(2, 3) = 3
        report = self.analyzer.analyze(slide_count=10, image_count=3)
        assert report.needs_ai_images is False
        assert report.deficit == 0

    def test_min_total_images_threshold(self):
        """Small presentations should still meet MIN_TOTAL_IMAGES."""
        # 3 slides, ratio target = int(3 * 0.3) = 0, but MIN_TOTAL = 2
        report = self.analyzer.analyze(slide_count=3, image_count=0)
        assert report.needs_ai_images is True
        assert report.deficit == 2  # MIN_TOTAL_IMAGES

    def test_min_total_images_satisfied(self):
        """Small presentations with enough images should be fine."""
        report = self.analyzer.analyze(slide_count=3, image_count=2)
        assert report.needs_ai_images is False
        assert report.deficit == 0

    def test_deficit_capped_at_max(self):
        """Deficit should never exceed MAX_AI_IMAGES."""
        # 30 slides, target = max(2, 9) = 9, deficit = 9
        # But capped at MAX_AI_IMAGES = 5
        report = self.analyzer.analyze(slide_count=30, image_count=0)
        assert report.needs_ai_images is True
        assert report.deficit == self.analyzer.MAX_AI_IMAGES

    def test_content_slides_excludes_title_summary(self):
        """Content slides should exclude title and summary (2 slides)."""
        report = self.analyzer.analyze(slide_count=10, image_count=0)
        assert report.content_slides == 8  # 10 - 2

    def test_content_slides_minimum_zero(self):
        """Content slides should not go below 0."""
        report = self.analyzer.analyze(slide_count=1, image_count=0)
        assert report.content_slides == 0  # max(0, 1 - 2) = 0

    def test_ratio_calculation(self):
        """Image-to-slide ratio should be calculated correctly."""
        report = self.analyzer.analyze(slide_count=20, image_count=5)
        assert report.image_to_slide_ratio == 0.25

    def test_report_fields_populated(self):
        """All fields in ImageDensityReport should be populated."""
        report = self.analyzer.analyze(slide_count=15, image_count=2)
        assert isinstance(report, ImageDensityReport)
        assert report.total_slides == 15
        assert report.image_count == 2
        assert report.content_slides == 13
        assert report.image_to_slide_ratio == pytest.approx(2 / 15)
        assert isinstance(report.needs_ai_images, bool)
        assert isinstance(report.deficit, int)

    def test_many_images_no_deficit(self):
        """Presentation with many images should not need more."""
        report = self.analyzer.analyze(slide_count=10, image_count=10)
        assert report.needs_ai_images is False
        assert report.deficit == 0
        assert report.image_to_slide_ratio == 1.0

    def test_thresholds_are_class_constants(self):
        """Thresholds should be accessible as class constants."""
        assert ImageDensityAnalyzer.MIN_IMAGES_PER_SLIDE_RATIO == 0.3
        assert ImageDensityAnalyzer.MIN_TOTAL_IMAGES == 2
        assert ImageDensityAnalyzer.MAX_AI_IMAGES == 5
