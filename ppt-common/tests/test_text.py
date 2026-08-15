"""Tests for ppt_common.text module."""

import pytest
from ppt_common.text import (
    is_cjk,
    is_cjk_char,
    is_cjk_ideograph,
    is_cjk_pair,
    merge_pdf_lines,
    split_sentences,
    HEADER_PATTERN,
    GARBAGE_PATTERN,
)


class TestIsCjk:
    """Tests for is_cjk() function."""

    def test_chinese_text(self):
        """Pure Chinese text should be detected as CJK."""
        assert is_cjk("传播学概述") is True

    def test_english_text(self):
        """Pure English text should not be detected as CJK."""
        assert is_cjk("Communication Theory") is False

    def test_mixed_chinese_english(self):
        """Mixed text should be detected based on majority."""
        assert is_cjk("传播学概述与理论基础简介") is True  # More CJK (12 vs 0)
        assert is_cjk("传播 Communication Theory Overview") is False  # More Latin (2 vs 24)

    def test_japanese_text(self):
        """Japanese text (with hiragana/katakana) should be detected as CJK."""
        assert is_cjk("コミュニケーション理論") is True

    def test_empty_string(self):
        """Empty string should return False."""
        assert is_cjk("") is False

    def test_numbers_only(self):
        """Numbers only should return False."""
        assert is_cjk("12345") is False

    def test_punctuation_only(self):
        """Punctuation only should return False."""
        assert is_cjk("。！？") is False


class TestIsCjkChar:
    """Tests for is_cjk_char() function."""

    def test_chinese_char(self):
        """Chinese character should be detected."""
        assert is_cjk_char("中") is True
        assert is_cjk_char("文") is True

    def test_chinese_punctuation(self):
        """Chinese punctuation should be detected."""
        assert is_cjk_char("。") is True
        assert is_cjk_char("，") is True
        assert is_cjk_char("！") is True

    def test_japanese_chars(self):
        """Japanese hiragana/katakana should be detected."""
        assert is_cjk_char("あ") is True  # hiragana
        assert is_cjk_char("ア") is True  # katakana

    def test_english_char(self):
        """English character should not be detected."""
        assert is_cjk_char("a") is False
        assert is_cjk_char("Z") is False

    def test_number(self):
        """Number should not be detected."""
        assert is_cjk_char("5") is False

    def test_ascii_punctuation(self):
        """ASCII punctuation should not be detected."""
        assert is_cjk_char(".") is False
        assert is_cjk_char(",") is False


class TestIsCjkPair:
    """Tests for is_cjk_pair() function."""

    def test_both_chinese(self):
        """Both Chinese characters should return True."""
        assert is_cjk_pair("中", "文") is True

    def test_one_chinese(self):
        """One Chinese character should return True."""
        assert is_cjk_pair("中", "a") is True
        assert is_cjk_pair("a", "中") is True

    def test_both_english(self):
        """Both English characters should return False."""
        assert is_cjk_pair("a", "b") is False

    def test_chinese_punctuation(self):
        """Chinese punctuation should trigger True."""
        assert is_cjk_pair("。", "a") is True


class TestMergePdfLines:
    """Tests for merge_pdf_lines() function."""

    def test_chinese_line_merge(self):
        """Chinese lines should merge without space."""
        lines = ["传播", "学概述"]
        result = merge_pdf_lines(lines)
        assert result == "传播学概述"

    def test_english_line_merge(self):
        """English lines should merge with space."""
        lines = ["hello", "world"]
        result = merge_pdf_lines(lines)
        assert result == "hello world"

    def test_empty_input(self):
        """Empty input should return empty string."""
        assert merge_pdf_lines([]) == ""

    def test_single_line(self):
        """Single line should return as-is."""
        assert merge_pdf_lines(["传播学"]) == "传播学"

    def test_paragraph_break_on_empty_line(self):
        """Empty lines should create paragraph breaks."""
        lines = ["第一段落", "", "第二段落"]
        result = merge_pdf_lines(lines)
        assert "第一段落" in result
        assert "第二段落" in result
        assert result.count("\n") >= 1

    def test_paragraph_break_on_sentence_end(self):
        """Sentence-ending punctuation should create paragraph break."""
        lines = ["这是第一句。", "这是第二句"]
        result = merge_pdf_lines(lines)
        assert result.count("\n") >= 1

    def test_header_detection(self):
        """Section headers should be kept separate."""
        lines = ["正文内容", "第一章 概述", "新的段落"]
        result = merge_pdf_lines(lines)
        assert "第一章 概述" in result
        # Header should be on its own line
        assert result.count("\n") >= 2

    def test_garbage_line_removal(self):
        """Garbage lines should be removed."""
        lines = ["正文", "  ", "更多正文"]
        result = merge_pdf_lines(lines)
        assert "正文" in result
        assert "更多正文" in result

    def test_mixed_content(self):
        """Mixed Chinese and English content."""
        lines = ["传播学", "Communication", "Theory"]
        result = merge_pdf_lines(lines)
        assert "传播学" in result
        assert "Communication" in result


class TestPatterns:
    """Tests for exported regex patterns."""

    def test_header_pattern_chinese(self):
        """Chinese chapter headers should match."""
        assert HEADER_PATTERN.match("第一章 概述")
        assert HEADER_PATTERN.match("第二章 传播")
        assert HEADER_PATTERN.match("第三章")

    def test_header_pattern_english(self):
        """English chapter headers should match."""
        assert HEADER_PATTERN.match("Chapter 1")
        assert HEADER_PATTERN.match("Section 2")
        assert HEADER_PATTERN.match("Part III")

    def test_header_pattern_numbered(self):
        """Numbered sections should match."""
        assert HEADER_PATTERN.match("1.1 Introduction")
        assert HEADER_PATTERN.match("2.3.4 Details")

    def test_garbage_pattern_empty(self):
        """Empty strings should match garbage pattern."""
        assert GARBAGE_PATTERN.match("")
        assert GARBAGE_PATTERN.match("   ")

    def test_garbage_pattern_short_non_cjk(self):
        """Short non-CJK strings should match garbage pattern."""
        assert GARBAGE_PATTERN.match("!")
        assert GARBAGE_PATTERN.match("??")

    def test_garbage_pattern_real_text(self):
        """Real text should not match garbage pattern."""
        assert not GARBAGE_PATTERN.match("传播学")
        assert not GARBAGE_PATTERN.match("Communication")


class TestIsCjkIdeograph:
    """Tests for is_cjk_ideograph() function."""

    def test_han_ideographs(self):
        assert is_cjk_ideograph("中") is True
        assert is_cjk_ideograph("文") is True

    def test_kana(self):
        assert is_cjk_ideograph("あ") is True  # hiragana
        assert is_cjk_ideograph("ア") is True  # katakana

    def test_hangul(self):
        assert is_cjk_ideograph("한") is True
        assert is_cjk_ideograph("글") is True

    def test_punctuation_excluded(self):
        """Unlike is_cjk_char, punctuation must NOT count."""
        assert is_cjk_ideograph("。") is False
        assert is_cjk_ideograph("，") is False

    def test_latin_excluded(self):
        assert is_cjk_ideograph("a") is False
        assert is_cjk_ideograph("1") is False


class TestSplitSentences:
    """Tests for split_sentences() function."""

    def test_cjk_auto_detect(self):
        assert split_sentences("第一句。第二句。") == ["第一句。", "第二句。"]

    def test_latin_auto_detect(self):
        assert split_sentences("First. Second!") == ["First.", " Second!"]

    def test_explicit_cjk_mode(self):
        result = split_sentences("一句话。", cjk_mode=True)
        assert result == ["一句话。"]

    def test_explicit_latin_mode(self):
        result = split_sentences("One. Two?", cjk_mode=False)
        assert result == ["One.", " Two?"]

    def test_min_length_filters_short_sentences(self):
        text = "短。这是一个足够长的句子，用来测试过滤。"
        result = split_sentences(text, min_length=10)
        assert all(len(s) > 10 for s in result)
        assert "短。" not in result

    def test_min_length_zero_returns_all(self):
        text = "短。长句子在这里呢。"
        assert len(split_sentences(text, min_length=0)) == 2

    def test_empty_text(self):
        assert split_sentences("") == []


# ---------------------------------------------------------------------------
# Mutation-gap tests (mutation-audit follow-up)
#
# Every assertion below is pinned to kill a specific mutant class that the
# original suite let through. Keep the exact-value assertions — weakening
# them to `in` / count checks re-opens the gap.
# ---------------------------------------------------------------------------

from ppt_common.text import clean_page, is_section_header, sanitize_text, is_pdf_section_header, merge_pdf_lines, extract_page_text, subbody_threshold  # noqa: E402


class TestUnicodeRangeBoundaries:
    """Exact boundary characters for the CJK/Kana/Hangul ranges.

    Kills <=/< boundary mutants in _in_range: each boundary char must be
    included, and its immediate neighbours excluded.
    """

    def test_han_range_boundaries(self):
        assert is_cjk_char("\u4e00") is True    # first Han ideograph
        assert is_cjk_char("\u9fff") is True    # last char in range
        assert is_cjk_char("\u4dff") is False   # just below
        assert is_cjk_char("\ua000") is False   # just above

    def test_kana_range_boundaries(self):
        assert is_cjk_char("\u3040") is True
        assert is_cjk_char("\u30ff") is True
        assert is_cjk_char("\u303f") is False
        assert is_cjk_char("\u3100") is False

    def test_ideograph_han_boundaries(self):
        assert is_cjk_ideograph("\u4e00") is True
        assert is_cjk_ideograph("\u9fff") is True
        assert is_cjk_ideograph("\u4dff") is False
        assert is_cjk_ideograph("\ua000") is False

    def test_ideograph_kana_boundaries(self):
        assert is_cjk_ideograph("\u3040") is True
        assert is_cjk_ideograph("\u30ff") is True
        assert is_cjk_ideograph("\u303f") is False
        assert is_cjk_ideograph("\u3100") is False

    def test_ideograph_hangul_boundaries(self):
        assert is_cjk_ideograph("\uac00") is True   # first Hangul syllable
        assert is_cjk_ideograph("\ud7af") is True   # last Hangul syllable
        assert is_cjk_ideograph("\uabff") is False
        assert is_cjk_ideograph("\ud7b0") is False

    def test_is_cjk_counts_boundary_chars(self):
        # Single boundary chars must be counted by is_cjk as well.
        assert is_cjk("\u4e00") is True
        assert is_cjk("\u9fff") is True
        assert is_cjk("\u3040\u30ff") is True


class TestIsCjkDecisionBoundary:
    """Pins the cjk>=latin / cjk>=3 decision logic in is_cjk."""

    def test_single_cjk_char_with_single_latin(self):
        # cjk == 1 > 0 and 1 >= 1 latin -> True (kills cjk > 1 mutant)
        assert is_cjk("\u4e2da") is True

    def test_equal_counts_cjk_wins(self):
        # 2 CJK == 2 latin: cjk >= latin -> True
        # (kills sum(2...), cjk > latin, and or->and mutants)
        assert is_cjk("\u4e2d\u6587ab") is True

    def test_cjk_majority_with_digits(self):
        # digits are ascii but not alpha -> latin stays 0
        # (kills isascii() and/or isalpha() -> or mutant)
        assert is_cjk("\u4e2d\u6587ab1") is True

    def test_three_cjk_floor_beats_latin_majority(self):
        # cjk=3 < latin=6 but cjk >= 3 floor -> True
        # (kills cjk > 3 and cjk >= 4 mutants)
        assert is_cjk("\u4e2d\u6587\u4e2dabcdef") is True

    def test_pure_katakana(self):
        # No kanji fallback — only the kana range can make this True
        # (kills kana-range XX-wrap mutants)
        assert is_cjk("\u30ab\u30bf\u30ab\u30ca") is True

    def test_pure_hiragana(self):
        assert is_cjk("\u3053\u3093\u306b\u3061\u306f") is True

    def test_ascii_letters_not_cjk_chars(self):
        # Guards against _CJK_PUNCT gaining stray members
        assert is_cjk_char("X") is False
        assert is_cjk_char("x") is False


class TestSanitizeText:
    """clean_page's sibling: sanitize_text had zero tests."""

    def test_removes_c0_control_chars(self):
        assert sanitize_text("ab\x00cd\x07ef\x1fx") == "abcdefx"

    def test_keeps_newline_tab_cr(self):
        assert sanitize_text("a\tb\nc\rd") == "a\tb\nc\rd"

    def test_pure_digit_hyphen_line_removed(self):
        assert sanitize_text("123-456-789") == ""
        assert sanitize_text("  42  ") == ""

    def test_isbn_removed_inside_text(self):
        # NOTE: _ISBN_RE matches exactly 4 groups, so a 5-group ISBN-13
        # leaves the trailing "-9". Pinned as-is for mutation auditing;
        # the residue is a known quirk (see audit report).
        assert sanitize_text("text 978-0-123456-78-9 more") == "text -9 more"

    def test_isbn_four_groups_removed(self):
        assert sanitize_text("text 0-123-45678-90 more") == "text  more"

    def test_isbn_like_four_groups(self):
        assert sanitize_text("x 099619-01-66670-7 y") == "x  y"

    def test_strips_outer_whitespace(self):
        assert sanitize_text("  hello  ") == "hello"

    def test_normal_text_passthrough(self):
        assert sanitize_text("Hello, 世界!") == "Hello, 世界!"

    def test_punctuation_only_fragments_removed(self):
        # Orphan punctuation must not survive as
        # standalone slide bullets/text boxes.
        assert sanitize_text(",") == ""
        assert sanitize_text("，") == ""
        assert sanitize_text("——") == ""
        assert sanitize_text("•") == ""
        assert sanitize_text("（）") == ""
        assert sanitize_text("…") == ""

    def test_empty_string_removed(self):
        assert sanitize_text("") == ""
        assert sanitize_text("   ") == ""

    def test_digit_punct_mix_kept(self):
        # Real content like decimals or enumerations with text stays.
        assert sanitize_text("3.14") == "3.14"
        assert sanitize_text("1,2") == "1,2"


class TestIsSectionHeader:
    """is_section_header had zero tests."""

    def test_l1_chinese_chapter(self):
        assert is_section_header("第一章 绪论") is True

    def test_l1_chinese_part(self):
        assert is_section_header("第3部分") is True

    def test_l1_chapter_english(self):
        assert is_section_header("Chapter 5") is True
        assert is_section_header("Part 2") is True

    def test_l2_chinese_section(self):
        assert is_section_header("第一节 传播的定义") is True

    def test_l2_numbered_section(self):
        assert is_section_header("1.2 Overview") is True

    def test_three_level_number_not_l2(self):
        # Quirk: _SECTION_L2 has no (?:\.\d+)? group, so 3-level numbers
        # are not L2 headers here (merge_pdf_lines' _HEADER_RE does accept
        # them). Pinned as-is for mutation auditing.
        assert is_section_header("2.3.4 Deep") is False

    def test_l2_section_english(self):
        assert is_section_header("Section 3") is True

    def test_l3_numbered_cjk(self):
        assert is_section_header("1. 概述") is True

    def test_l3_numbered_latin_upper(self):
        assert is_section_header("2. Overview") is True

    def test_body_text_not_header(self):
        assert is_section_header("这是一段很长的段落内容，描述了很多细节的东西。") is False

    def test_length_cutoff(self):
        header = "第一章 " + "长" * 40
        assert is_section_header(header) is False

    def test_exact_max_length_accepted(self):
        header = "第一章 " + "长" * 26   # exactly 30 chars
        assert len(header) == 30
        assert is_section_header(header) is True

    def test_custom_max_length(self):
        assert is_section_header("第一章 绪论", max_length=4) is False


class TestCleanPage:
    """clean_page had zero tests (147 unaudited mutants)."""

    def test_removes_standalone_page_numbers(self):
        assert clean_page("line one\n123\nline two", 1) == "line one\nline two"

    def test_removes_standalone_footnote_marker(self):
        assert clean_page("text here\na\nmore text", 1) == "text here\nmore text"

    def test_removes_book_title_running_header(self):
        assert clean_page("传播学教程\nbody text", 1, book_title="传播学教程") == "body text"

    def test_removes_chapter_title_running_header(self):
        assert clean_page("第三章 背景\nbody text", 1, chapter_title="第三章 背景") == "body text"

    def test_removes_cjk_chapter_running_header(self):
        # Matches ^第.+章\s and len < 20
        assert clean_page("第五章 内容\nreal content", 1) == "real content"

    def test_removes_chapter_n_running_header(self):
        assert clean_page("Chapter 5\nreal content", 1) == "real content"

    def test_cleans_inline_footnote_ref_cjk_punct(self):
        assert clean_page("这是内容。a", 1) == "这是内容。"

    def test_cleans_inline_footnote_ref_latin_punct(self):
        assert clean_page("some content.a", 1) == "some content."

    def test_cleans_trailing_letter_after_space(self):
        assert clean_page("words here b", 1) == "words here"

    def test_removes_control_chars(self):
        assert clean_page("ab\x01cd", 1) == "abcd"

    def test_drops_garbage_dominated_lines(self):
        # 6 chars, none CJK/ASCII -> ratio 0 < 0.5 -> dropped
        assert clean_page("◆◆◆◆◆◆\ngood line", 1) == "good line"

    def test_strips_embedded_edition_header(self):
        assert clean_page("前言（第2版）说明", 1) == "说明"

    def test_empty_input(self):
        assert clean_page("", 1) == ""

    def test_blank_lines_skipped(self):
        assert clean_page("one\n\n   \ntwo", 1) == "one\ntwo"

    def test_multiline_roundtrip(self):
        raw = "传播学教程\n第一章 绪论\n77\n正文内容\na\n结尾。b"
        assert clean_page(raw, 1, book_title="传播学教程") == "正文内容\n结尾。"

    # Regression: the garbage-strip allowlist dropped / - % & + = ~ and the en
    # dash from body text ("1/10000" -> "1 10000" etc.). Regression oracles
    # come from the 2026-08-13 dogfood deck (textbook-publishing-standards).

    def test_preserves_slash_in_fraction(self):
        assert clean_page("编校差错率不超过1/10000。", 1) == "编校差错率不超过1/10000。"

    def test_preserves_slash_in_standard_number(self):
        assert clean_page("GB/T 15834 与 GB/T 15835", 1) == "GB/T 15834 与 GB/T 15835"

    def test_preserves_hyphen_in_k12(self):
        assert clean_page("K-12 教材还要对齐课程标准", 1) == "K-12 教材还要对齐课程标准"

    def test_preserves_hyphen_in_figure_number(self):
        assert clean_page("（图3-2）且正文必须引用", 1) == "（图3-2）且正文必须引用"

    def test_preserves_hyphen_in_range(self):
        assert clean_page("GB 3100-3102 保留连字符", 1) == "GB 3100-3102 保留连字符"

    def test_preserves_percent_amp_plus_equals_tilde_endash(self):
        assert clean_page("增长20%、A&B、x+y、a=b、约5~6件、2001–2010", 1) == (
            "增长20%、A&B、x+y、a=b、约5~6件、2001–2010"
        )

    def test_still_strips_box_drawing_garbage(self):
        assert clean_page("正文──│█│──结束", 1) == "正文 结束"


class TestMergePdfLinesMutationGaps:
    """Targets mutants the original merge tests missed."""

    def test_backspace_removed(self):
        assert merge_pdf_lines(["ab\x08cd"]) == "abcd"

    def test_zero_width_space_removed(self):
        assert merge_pdf_lines(["ab\u200bcd"]) == "abcd"

    def test_content_after_garbage_line(self):
        # "--" is garbage (non-word, non-CJK, <=3 chars) -> paragraph break;
        # the next line must start a fresh paragraph, not append to garbage
        # state. Exact assertion kills reset-state and join mutants.
        assert merge_pdf_lines(["para1", "--", "para2"]) == "para1\npara2"

    def test_content_after_header(self):
        # After a standalone header, the next content line must start a new
        # paragraph cleanly.
        result = merge_pdf_lines(["intro", "第一章 绪论", "content"])
        assert result == "intro\n第一章 绪论\ncontent"

    def test_cjk_join_depends_on_last_char(self):
        # current ends CJK ('中') but second-to-last is Latin ('A'):
        # join must be space-free because the LAST char is CJK.
        # (kills current[-2] mutant)
        assert merge_pdf_lines(["A\u4e2d", "bc"]) == "A\u4e2dbc"

    def test_latin_tail_forces_space_join(self):
        # current ends Latin ('A'), second char is CJK: the LAST char
        # decides -> space join. (kills current[+1] mutant)
        assert merge_pdf_lines(["\u4e2d\u4e2dA", "bc"]) == "\u4e2d\u4e2dA bc"

    def test_first_char_of_next_line_decides(self):
        # Latin current + CJK first char of next line -> space-free join.
        # (kills line[1] mutant)
        assert merge_pdf_lines(["abc", "\u4e2dx"]) == "abc\u4e2dx"

    def test_latin_x_is_not_sentence_end(self):
        # Guards _SENTENCE_ENDS against gaining stray members: a line
        # ending in 'X' must still merge with the next line.
        assert merge_pdf_lines(["lineX", "more"]) == "lineX more"

    def test_sentence_end_creates_exact_break(self):
        assert merge_pdf_lines(["第一句。", "第二句"]) == "第一句。\n第二句"


class TestSplitSentencesMutationGaps:
    """Boundary behaviour of the min_length filter."""

    def test_exact_min_length_excluded(self):
        # "AB." strips to len 3 == min_length -> excluded by strict >
        result = split_sentences("AB. CDEF.", cjk_mode=False, min_length=3)
        assert result == ["CDEF."]

    def test_one_over_min_length_included(self):
        result = split_sentences("ABCD. EF.", cjk_mode=False, min_length=3)
        assert result == ["ABCD."]

    def test_min_length_one_keeps_all(self):
        # Every regex-matched sentence is >= 2 chars, so min_length=1
        # keeps everything (pins the filter branch at the low end).
        assert split_sentences("短。 longer one here。", cjk_mode=True,
                               min_length=1) == ["短。", "longer one here。"]


class TestCleanPageMutationGaps:
    """Round-2 gap killers: boundary lengths, ratios, and regex anchors."""

    def test_inline_garbage_replaced_with_space(self):
        # Kills XX-wrap mutants on the garbage-strip pattern (they stop
        # matching runs that lack the literal XX affixes).
        assert clean_page("ab\u25c6\u25c6cd", 1) == "ab cd"

    def test_uppercase_latin_kept(self):
        # Kills the a-zA-Z -> a-za-z class mutant (uppercase would be
        # treated as garbage and stripped).
        assert clean_page("HELLO \u4e16\u754c", 1) == "HELLO \u4e16\u754c"

    def test_default_title_args_are_empty(self):
        # Kills book_title=""->XXXX / chapter_title=""->XXXX mutants:
        # a line equal to "XXXX" must survive when no titles are passed.
        assert clean_page("XXXX\nbody", 1) == "XXXX\nbody"

    def test_double_space_collapsed(self):
        # Kills the \\s+ -> XX\\s+XX mutants on the first collapse pass.
        # (Two-char tail: a single trailing lowercase letter after
        # whitespace is stripped earlier by the footnote-ref rule.)
        assert clean_page("a  bc", 1) == "a bc"

    def test_collapse_after_edition_removal(self):
        # Kills the second collapse-pass mutant (fires only when the
        # edition-header removal leaves extra whitespace).
        assert clean_page("\u524d\u8a00\uff08\u7b2c2\u7248\uff09  \u8bf4\u660e", 1) == "\u8bf4\u660e"

    def test_ratio_len5_boundary_kept(self):
        # len == 5 is NOT > 5 -> kept (kills len >= 5 mutant and the
        # or/and swap on the same condition).
        assert clean_page("\uff0c\uff0c\uff0c\uff0c\uff0c", 1) == "\uff0c\uff0c\uff0c\uff0c\uff0c"

    def test_ratio_len6_garbage_dropped(self):
        # len 6, ratio 0 -> dropped; also kills continue->break (the
        # following line must still be processed).
        assert clean_page("\uff0c\uff0c\uff0c\uff0c\uff0c\uff0c\n\u4fdd\u7559", 1) == "\u4fdd\u7559"

    def test_ratio_below_half_dropped(self):
        # 3 cjk_ascii of 7 chars = 0.43 -> dropped. Kills sum(2...) and
        # cjk_ascii * len mutants (both would keep the line).
        assert clean_page("\uff0c\uff0c\uff0c\uff0cab\u4e2d\n\u4fdd\u7559", 1) == "\u4fdd\u7559"

    def test_ratio_ascii_undercount_dropped(self):
        # 2 cjk_ascii of 6 = 0.33 -> dropped. Kills the XX-wrap lower
        # bound mutant (which would start counting ASCII letters as CJK).
        assert clean_page("\uff0c\uff0c\uff0c\uff0cab\n\u4fdd\u7559", 1) == "\u4fdd\u7559"

    def test_ratio_exactly_half_kept_with_boundary_chars(self):
        # 3 cjk_ascii of 6 = exactly 0.5 -> kept. The counted chars are
        # 'a', U+4E00 and U+9FFF, so any <=/< boundary mutant in the
        # range check drops the ratio below 0.5 and the line disappears.
        line = "\uff0c\uff0c\uff0ca\u4e00\u9fff"
        assert clean_page(line + "\n\u4fdd\u7559", 1) == line + "\n\u4fdd\u7559"

    def test_cjk_chapter_len20_kept(self):
        # len == 20 is NOT < 20 -> kept (kills <= 20 / < 21 mutants).
        line = "\u7b2c\u4e00\u7ae0 " + "\u6761" * 16
        assert len(line) == 20
        assert clean_page(line, 1) == line

    def test_cjk_chapter_len19_dropped(self):
        line = "\u7b2c\u4e00\u7ae0 " + "\u6761" * 15
        assert len(line) == 19
        assert clean_page(line + "\n\u4fdd\u7559", 1) == "\u4fdd\u7559"

    def test_chapter_num_len30_kept(self):
        # len == 30 is NOT < 30 -> kept (kills <= 30 / < 31 mutants).
        line = "Chapter " + "1" * 22
        assert len(line) == 30
        assert clean_page(line, 1) == line

    def test_chapter_num_len29_dropped(self):
        line = "Chapter " + "1" * 21
        assert len(line) == 29
        assert clean_page(line + "\n\u4fdd\u7559", 1) == "\u4fdd\u7559"

    def test_chapter_num_uppercase_dropped(self):
        assert clean_page("CHAPTER 5\n\u4fdd\u7559", 1) == "\u4fdd\u7559"

    def test_control_chars_incl_nul_removed(self):
        assert clean_page("ab\x00cd\x07ef", 1) == "abcdef"
        assert clean_page("a\x0bbc", 1) == "abc"
        assert clean_page("a\x0ebc", 1) == "abc"
        assert clean_page("a\x1fbc", 1) == "abc"

    def test_tab_cr_space_preserved(self):
        # Kills chr() boundary mutants that would widen the control
        # class into tab (0x09), CR (0x0D) or space (0x20). The tab is
        # not removed, only collapsed to a space by the \\s+ pass.
        assert clean_page("a\tbc", 1) == "a bc"
        assert clean_page("a\rbc", 1) == "a bc"
        assert clean_page("a bc", 1) == "a bc"

    def test_edition_header_boundary_prefixes(self):
        # Prefixes containing the exact Han-range endpoints must still
        # match (kills chr(0x4E00)+1 / chr(0x9FFF)+1 mutants).
        assert clean_page("\u4e00\u767d\uff08\u7b2c2\u7248\uff09\u8bf4\u660e", 1) == "\u8bf4\u660e"
        assert clean_page("\u9fff\u767d\uff08\u7b2c2\u7248\uff09\u8bf4\u660e", 1) == "\u8bf4\u660e"

    def test_edition_header_ascii_prefix_not_removed(self):
        # 'X' is not a Han ideograph: kills XX-wrap mutants on the
        # edition pattern that would add stray members to the class.
        line = "X\u767d\uff08\u7b2c2\u7248\uff09\u8bf4\u660e"
        assert clean_page(line, 1) == line


class TestIsSectionHeaderMutationGaps:

    def test_len31_header_rejected_with_default(self):
        # Kills the max_length default 30 -> 31 mutant.
        header = "\u7b2c\u4e00\u7ae0 " + "\u957f" * 27
        assert len(header) == 31
        assert is_section_header(header) is False


class TestPdfSectionHeaderDetection:
    """Extended header detection for "N 标题" documents."""

    def test_numbered_cjk_headers_detected(self):
        assert is_pdf_section_header("1 问题：名家教材为什么耐读")
        assert is_pdf_section_header("2 三层标准体系")
        assert is_pdf_section_header("5 可迁移的设计思路")

    def test_standalone_section_words_detected(self):
        assert is_pdf_section_header("总结")
        assert is_pdf_section_header("参考资料")
        assert is_pdf_section_header("摘要")

    def test_legacy_patterns_still_detected(self):
        assert is_pdf_section_header("第三章 背景")
        assert is_pdf_section_header("2.1 风格层：house style 与体例书")
        assert is_pdf_section_header("Chapter 5 Introduction")

    def test_fragments_and_sentences_rejected(self):
        assert not is_pdf_section_header("18 版）")
        assert not is_pdf_section_header("")
        assert not is_pdf_section_header(
            "3 个实验表明，稳定性来自体例书而不是天才作者，这一点很重要"
        )
        assert not is_pdf_section_header("这是一段普通的正文内容，不是标题。")

    def test_merge_keeps_numbered_header_standalone(self):
        merged = merge_pdf_lines(["结尾无障碍", "1 问题：名家教材为什么耐读", "先做三个小实验"])
        lines = merged.split("\n")
        assert "1 问题：名家教材为什么耐读" in lines, (
            "numbered CJK header glued into a paragraph hides the section"
        )

    def test_merge_keeps_standalone_word_header(self):
        merged = merge_pdf_lines(["进入市场的门票。", "总结", "名家教材的秘密不在天才作者"])
        assert merged.split("\n")[1] == "总结"


# ---------------------------------------------------------------------------
# TRA-396: span-size footnote filtering
# ---------------------------------------------------------------------------


def _fn_blocks(lines):
    return [
        {
            "type": 0,
            "lines": [
                {"spans": [{"text": t, "size": s} for t, s in line]} for line in lines
            ],
        }
    ]


class TestSubbodyThreshold:
    def test_modal_body_size_sets_cutoff(self):
        body = [[(f"body line number {i} here", 10.5)] for i in range(6)]
        blocks = _fn_blocks(body + [
            [("a", 6.1)],
            [("footnote text", 7.5)],
        ])
        assert subbody_threshold(blocks) == 0.85 * 10.5

    def test_sparse_pages_return_zero(self):
        blocks = _fn_blocks([
            [("big title", 22.0)],
            [("small author line", 12.0)],
        ])
        assert subbody_threshold(blocks) == 0.0

    def test_no_text_spans_returns_zero(self):
        assert subbody_threshold([]) == 0.0
        assert subbody_threshold([{"type": 1, "lines": []}]) == 0.0


class TestExtractPageText:
    def test_drops_footnote_and_inline_marker_spans(self):
        fitz = pytest.importorskip("fitz")
        doc = fitz.open()
        page = doc.new_page()
        for i, y in enumerate((100, 120, 140, 160, 180, 200)):
            page.insert_text((72, y), f"body line number {i} here.", fontsize=10.5)
        page.insert_text((72, 220), "body four", fontsize=10.5)
        page.insert_text((140, 160), "a", fontsize=6.1)
        page.insert_text((150, 160), " tail.", fontsize=10.5)
        page.insert_text((72, 700), "a footnote line.", fontsize=7.5)
        page.insert_text((72, 712), "footnote continuation.", fontsize=7.5)

        text = extract_page_text(page)
        doc.close()

        assert "footnote" not in text
        lines = text.split("\n")
        assert "body line number 0 here." in lines
        assert "a" not in lines
        joined = "".join(lines)
        assert "body four" in joined and "tail." in joined
