"""Tests for ppt_common.text_metrics (shared typography metrics).

Ground-truth calibration per AGENTS.md verification rule 3: estimates are
compared against real font metrics (PIL/FreeType) on system CJK fonts.
"""

import platform

import pytest

from ppt_common.text_metrics import (
    BOLD_FACTOR,
    _wrap_units,
    estimate_lines,
    estimate_text_width,
    fit_font_size,
    fits,
    char_width_em,
    measure_text_width,
    wrap_text,
)

# Real CJK-capable system fonts for ground-truth measurement.
_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",          # macOS
    "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS
    "/System/Library/Fonts/STHeiti Medium.ttc",    # macOS
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # linux
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",       # linux
]


def _ground_truth_font() -> str | None:
    import os

    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


class TestCharWidthSpec:
    """The em table is a spec; pin it."""

    def test_cjk_ideograph(self):
        assert char_width_em("中") == 1.0

    def test_cjk_punctuation(self):
        assert char_width_em("，") == 1.0

    def test_space(self):
        assert char_width_em(" ") == 0.3

    def test_wide_latin(self):
        for ch in "mMwWOQ%":
            assert char_width_em(ch) == 0.75

    def test_narrow_latin(self):
        for ch in "iIlj!|":
            assert char_width_em(ch) == 0.3

    def test_digits(self):
        assert char_width_em("1") == 0.55

    def test_default_latin(self):
        assert char_width_em("a") == 0.55


class TestEstimateWidth:
    def test_pure_cjk(self):
        assert estimate_text_width("你好世界", 20) == pytest.approx(80.0)

    def test_bold_factor(self):
        plain = estimate_text_width("hello", 20)
        bold = estimate_text_width("hello", 20, bold=True)
        assert bold == pytest.approx(plain * BOLD_FACTOR)

    def test_headroom(self):
        plain = estimate_text_width("hello", 20)
        assert estimate_text_width("hello", 20, headroom=1.06) == pytest.approx(
            plain * 1.06
        )

    def test_unit_agnostic(self):
        # px in -> px out; pt in -> pt out (same ratio)
        assert estimate_text_width("测试", 36) / 36 == pytest.approx(
            estimate_text_width("测试", 20) / 20
        )


class TestEstimateLinesAndFits:
    def test_single_line(self):
        assert estimate_lines("短", 20, 800) == 1

    def test_wrap_two_lines(self):
        # 40 CJK chars @20px = 800 wide; box 500 -> 2 lines
        assert estimate_lines("中" * 40, 20, 500) == 2

    def test_explicit_newlines(self):
        assert estimate_lines("中\n中", 20, 800) == 2

    def test_empty_line_counts(self):
        assert estimate_lines("\n", 20, 800) == 2

    def test_fits_height(self):
        # 2 lines * 20px * 1.2 = 48 > 40 -> does not fit
        assert not fits("中" * 40, 20, 500, 40)
        assert fits("中" * 40, 20, 500, 60)


class TestFitFontSize:
    def test_no_shrink_when_fits(self):
        assert fit_font_size("短标题", 800, 100, max_size=44) == 44

    def test_shrinks_long_text(self):
        size = fit_font_size("中" * 60, 800, 60, max_size=44)
        assert 8 < size < 44
        assert fits("中" * 60, size, 800, 60)

    def test_monotonicity_boundary(self):
        text = "这是一个非常非常长的标题用来测试二分搜索字号拟合算法的正确性"
        size = fit_font_size(text, 800, 60)
        assert fits(text, size, 800, 60)
        assert not fits(text, size + 0.5, 800, 60)

    def test_overflow_returns_min(self):
        size = fit_font_size("中" * 500, 100, 20, min_size=8)
        assert size == 8

    def test_empty_text(self):
        assert fit_font_size("", 800, 60, max_size=44) == 44


class TestWrapText:
    def test_short_line_unchanged(self):
        assert wrap_text("短", 20, 800) == ["短"]

    def test_cjk_breaks_per_char(self):
        lines = wrap_text("中" * 40, 20, 500)
        assert len(lines) == 2
        assert all(estimate_text_width(l, 20) <= 500 * 1.01 for l in lines)

    def test_latin_word_not_split(self):
        lines = wrap_text("hello world foo", 20, 200)
        joined_lines = lines
        for word in ("hello", "world", "foo"):
            assert sum(word in line for line in joined_lines) == 1

    def test_explicit_newline_preserved(self):
        assert wrap_text("a\nb", 20, 800) == ["a", "b"]

    def test_wrapped_lines_respect_headroom(self):
        lines = wrap_text("测试文本" * 20, 20, 600)
        for line in lines:
            assert estimate_text_width(line, 20) <= 600 / 1.06 * 1.02


class TestGroundTruth:
    """Estimate vs real FreeType metrics (AGENTS.md rule 3)."""

    CORPUS_CJK = [
        "本书系统地介绍了机器学习的基础理论与前沿进展",
        "第七章　深度学习模型优化与正则化方法",
        "图7-2　不同学习率下的收敛曲线对比",
        "（一）研究背景与意义；（二）主要内容安排",
    ]
    CORPUS_MIXED = [
        "Transformer 模型在 NLP 任务中的表现优于 RNN",
        "GPU 集群训练效率提升 3.5 倍（见表 7-1）",
        "API 设计遵循 REST 规范，支持 OAuth2 认证",
        "p < 0.05 时差异显著，95% 置信区间不含零",
    ]

    @pytest.fixture()
    def font_path(self):
        path = _ground_truth_font()
        if path is None:
            pytest.skip("no CJK system font available for ground truth")
        return path

    @pytest.mark.parametrize("size", [20, 24, 36])
    @pytest.mark.parametrize("text", CORPUS_CJK, ids=lambda t: t[:6])
    def test_cjk_within_10pct(self, font_path, text, size):
        measured = measure_text_width(text, size, font_path)
        if measured is None:
            pytest.skip("font load failed")
        est = estimate_text_width(text, size)
        assert abs(est - measured) / measured <= 0.10, (
            f"est={est:.1f} measured={measured:.1f}"
        )

    @pytest.mark.parametrize("size", [20, 36])
    @pytest.mark.parametrize("text", CORPUS_MIXED, ids=lambda t: t[:6])
    def test_mixed_within_15pct(self, font_path, text, size):
        measured = measure_text_width(text, size, font_path)
        if measured is None:
            pytest.skip("font load failed")
        est = estimate_text_width(text, size)
        assert abs(est - measured) / measured <= 0.15, (
            f"est={est:.1f} measured={measured:.1f}"
        )


class TestMutationGaps:
    """Assertion gaps surfaced by the mutmut mutation-audit pilot.

    Each test kills at least one surviving mutant; defaults, guard clauses,
    kwarg propagation and wrap boundaries are pinned explicitly.
    """

    # ── estimate_lines: defaults, guards, kwargs ────────────────────────────

    def test_lines_default_bold_is_false(self):
        # 150px plain fits 155; bold (157.5) would not — pins the default
        assert estimate_lines("m" * 10, 20, 155) == 1
        assert estimate_lines("m" * 10, 20, 155) == estimate_lines(
            "m" * 10, 20, 155, bold=False
        )

    def test_lines_bold_true_propagates(self):
        assert estimate_lines("m" * 10, 20, 155, bold=True) == 2

    def test_lines_headroom_propagates(self):
        assert estimate_lines("m" * 10, 20, 155, headroom=1.06) == 2

    def test_lines_zero_box_width(self):
        assert estimate_lines("x", 20, 0) == 0

    def test_lines_negative_box_width(self):
        assert estimate_lines("x", 20, -5) == 0

    def test_lines_unit_box_width(self):
        # 11px-wide glyph into a 1px box -> 11 lines (guard must not eat this)
        assert estimate_lines("x", 20, 1) == 11

    # ── fits: guard clauses and inclusive boundary ──────────────────────────

    def test_fits_guard_non_positive_font(self):
        assert not fits("x", 0, 100, 100)
        assert not fits("x", -5, 100, 100)

    def test_fits_guard_non_positive_width(self):
        assert not fits("x", 20, 0, 100)
        assert not fits("x", 20, -5, 100)

    def test_fits_guard_non_positive_height(self):
        assert not fits("x", 20, 100, 0)
        assert not fits("x", 0, 100, 0)

    def test_fits_unit_box_width(self):
        assert fits("x", 20, 1, 300)

    def test_fits_unit_box_height(self):
        assert fits("x", 0.01, 100, 1)

    def test_fits_unit_font_size(self):
        assert fits("x", 1, 100, 100)

    def test_fits_bold_true_tighter(self):
        assert fits("m" * 10, 20, 155, 26)
        assert not fits("m" * 10, 20, 155, 26, bold=True)

    def test_fits_exact_height_is_inclusive(self):
        # 1 line * 20 * 1.2 == 24: <= must accept the exact boundary
        assert fits("中" * 10, 20, 200, 24)

    # ── fit_font_size: defaults, kwargs, loop precision ─────────────────────

    def test_fit_default_bold_is_false(self):
        assert fit_font_size("m" * 10, 170, 120) == 44

    def test_fit_bold_true_shrinks_more(self):
        size = fit_font_size("m" * 10, 170, 120, bold=True)
        assert size < 44
        assert fits("m" * 10, size, 170, 120, bold=True)
        assert not fits("m" * 10, size + 0.5, 170, 120, bold=True)

    def test_fit_min_check_respects_bold(self):
        # bold overflows at min (2 lines*24 > 30), plain would fit: must
        # return min_size, not search
        assert fit_font_size("m" * 10, 155, 30, min_size=20, bold=True) == 20

    def test_fit_max_check_respects_line_height(self):
        size = fit_font_size("中" * 4, 200, 60, line_height=2.0)
        assert size < 44
        assert fits("中" * 4, size, 200, 60, line_height=2.0)
        assert not fits("中" * 4, size + 0.5, 200, 60, line_height=2.0)

    def test_fit_min_check_respects_line_height(self):
        assert fit_font_size("中" * 5, 200, 60, min_size=40, line_height=2.0) == 40

    def test_fit_min_check_respects_small_line_height(self):
        # line_height below the 1.2 default: min fits at 1.0 but not at 1.2,
        # so the search must run instead of collapsing to min_size
        size = fit_font_size("中", 200, 9, line_height=1.0)
        assert size > 8
        assert fits("中", size, 200, 9, line_height=1.0)
        assert not fits("中", size + 0.5, 200, 9, line_height=1.0)

    def test_fit_loop_stops_at_quarter_precision(self):
        # hi-lo == 0.25 at entry: loop must NOT run (>= would over-refine)
        assert fit_font_size("中" * 10, 200, 24, min_size=19.85, max_size=20.1) == 19.85

    # ── wrap_text: defaults, boundaries, strip direction ────────────────────

    def test_wrap_default_bold_is_false(self):
        assert len(wrap_text("mmmmm mmmmm", 20, 170)) == 1

    def test_wrap_bold_true_wraps_earlier(self):
        assert len(wrap_text("mmmmm mmmmm", 20, 170, bold=True)) == 2

    def test_wrap_newlines_not_whitespace_split(self):
        assert wrap_text("a b\nc d", 20, 800) == ["a b", "c d"]

    def test_wrap_width_accumulator_starts_at_zero(self):
        assert wrap_text("中中", 20, 40, headroom=1.0) == ["中中"]

    def test_wrap_boundary_is_strictly_greater(self):
        # exact fit (80px into 80px usable) must stay on one line
        assert wrap_text("中中 中中", 20, 100, headroom=1.0) == ["中中 中中"]

    def test_wrap_emitted_line_rstripped(self):
        assert wrap_text("aa bb", 20, 30, headroom=1.0) == ["aa", "bb"]

    def test_wrap_continuation_lstrips_spaces_only(self):
        assert wrap_text("aa \tbb", 20, 30, headroom=1.0) == ["aa", "\tbb"]

    def test_wrap_continuation_keeps_non_space_prefix(self):
        assert wrap_text("中 Xbb", 20, 58, headroom=1.0) == ["中", "Xbb"]

    # ── _wrap_units: unit splitting ─────────────────────────────────────────

    def test_wrap_units_mixed_cjk_latin(self):
        assert _wrap_units("ab中 cd") == ["ab", "中", " cd"]

    def test_wrap_units_trailing_word(self):
        assert _wrap_units("ab") == ["ab"]

    def test_wrap_units_spaces_flush_on_next_word(self):
        assert _wrap_units("a b c") == ["a ", "b ", "c"]
