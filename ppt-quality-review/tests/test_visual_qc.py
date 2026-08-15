"""Tests for the render-level visual QC loop components."""

import base64

import pytest
from PIL import Image

from ppt_quality_review import svg_render
from ppt_quality_review.visual_qc import (
    SEVERITY,
    VisualReview,
    PageReview,
    feedback_from_gate,
    feedback_from_review,
    parse_page_review,
    review_rendered_pages,
)


class FakeVLM:
    """Counts calls; returns canned raw JSON per page index."""

    def __init__(self, responses: dict | None = None, default: str = ""):
        self.calls = 0
        self.responses = responses or {}
        self.default = default or '{"passed": true, "issues": [], "reason": "ok"}'

    def chat_with_images(self, user_prompt, image_paths, **kwargs):
        self.calls += 1
        return self.default


def _rec(name="01.svg", ok=True, sha="abc", blank=False, path="/tmp/x.png"):
    return {"page": name, "ok": ok, "sha256": sha,
            "all_background": blank, "path": path,
            **({} if ok else {"error": "boom"})}


class TestParsePageReview:
    def test_valid(self):
        r = parse_page_review('{"passed": false, "issues": ["tofu_boxes"], "reason": "r"}', 2)
        assert r.page_index == 2 and not r.passed
        assert r.blocking == ["tofu_boxes"] and r.cosmetic == []

    def test_passed_tristate(self):
        cases = [
            ('{"passed": true}', True),
            ('{"passed": "true"}', True),
            ('{"passed": "YES"}', True),
            ('{"passed": 1}', True),
            ('{"passed": false}', False),
            ('{"passed": 0}', False),
            ('{"passed": null}', False),
            ('{}', False),
        ]
        for raw, expect in cases:
            assert parse_page_review(raw, 1).passed is expect, raw

    def test_issues_not_list_coerced(self):
        r = parse_page_review('{"passed": true, "issues": "overlap"}', 1)
        assert r.issues == ["overlap"] and r.cosmetic == ["overlap"]

    def test_unknown_issue_maps_to_cosmetic(self):
        r = parse_page_review('{"passed": false, "issues": ["weird_thing"]}', 1)
        assert r.issues == ["low_quality_artifacts"]
        assert r.blocking == []

    def test_unparseable_yields_parse_error(self):
        r = parse_page_review("not json", 3)
        assert r.passed and r.issues == ["parse_error"]
        assert SEVERITY["parse_error"] == "cosmetic"


class TestReviewRenderedPages:
    def test_blank_page_flagged_without_vlm(self):
        vlm = FakeVLM()
        review = review_rendered_pages([_rec(blank=True)], ["brief"], client=vlm)
        assert review.blocking == [(1, "blank_page")]
        assert vlm.calls == 0

    def test_render_failure_is_cosmetic(self):
        vlm = FakeVLM()
        review = review_rendered_pages([_rec(ok=False)], ["brief"], client=vlm)
        assert review.blocking == []
        assert (1, "render_error") in review.cosmetic
        assert vlm.calls == 0

    def test_cache_hit_skips_vlm(self):
        vlm = FakeVLM()
        pages = [_rec(sha="s1"), _rec(name="02.svg", sha="s2")]
        cache: dict = {}
        review_rendered_pages(pages, ["a", "b"], client=vlm, cache=cache)
        assert vlm.calls == 2
        # second pass with same hashes: no new calls
        review_rendered_pages(pages, ["a", "b"], client=vlm, cache=cache)
        assert vlm.calls == 2
        assert len(cache) == 2

    def test_changed_page_re_reviewed(self):
        vlm = FakeVLM()
        cache: dict = {}
        review_rendered_pages([_rec(sha="s1")], ["a"], client=vlm, cache=cache)
        review_rendered_pages([_rec(sha="s1-changed")], ["a"], client=vlm, cache=cache)
        assert vlm.calls == 2


class TestFeedback:
    def test_blocking_first_cosmetic_capped(self):
        review = VisualReview(enabled=True, pages=[
            PageReview(1, True, ["overlap", "contract_violation",
                                 "low_quality_artifacts", "overlap"]),
            PageReview(2, False, ["overflow_clipped"]),
        ])
        fb = feedback_from_review(review)
        lines = fb.splitlines()
        assert "[blocking]" in lines[1]
        assert sum("[cosmetic]" in l for l in lines) == 3

    def test_empty_when_clean(self):
        assert feedback_from_review(VisualReview(enabled=True)) == ""

    def test_gate_feedback_extracts_errors(self):
        gate = {"output": "noise\n[ERROR] 02.svg text exceeds canvas\nmore\n"}
        fb = feedback_from_gate(gate)
        assert "02.svg text exceeds canvas" in fb

    def test_gate_feedback_fallback_tail(self):
        gate = {"output": "just some output without error lines"}
        fb = feedback_from_gate(gate)
        assert "just some output" in fb


class TestSvgRender:
    def test_all_background_solid(self, tmp_path):
        img = Image.new("RGB", (1280, 720), (15, 23, 42))
        path = tmp_path / "solid.png"
        img.save(path)
        assert svg_render.is_all_background(path) is True

    def test_all_background_noisy(self, tmp_path):
        import random
        random.seed(7)
        img = Image.new("RGB", (1280, 720))
        img.putdata([(random.randint(0, 255),) * 3 for _ in range(1280 * 720)])
        path = tmp_path / "noisy.png"
        img.save(path)
        assert svg_render.is_all_background(path) is False

    def test_backend_missing_degrades(self, tmp_path, monkeypatch):
        # playwright is not installed in the test env -> graceful degradation
        svg_render.reset_backend_probe_cache()
        monkeypatch.setitem(__import__("sys").modules, "playwright", None)
        assert svg_render.render_backend_available() is False
        svg_dir = tmp_path / "svg"
        svg_dir.mkdir()
        (svg_dir / "01.svg").write_text("<svg/>")
        result = svg_render.render_svg_dir(svg_dir, tmp_path / "out")
        assert result["ok"] is False
        assert result["error"] == "backend_missing"
        svg_render.reset_backend_probe_cache()

    def test_no_svgs(self, tmp_path):
        result = svg_render.render_svg_dir(tmp_path, tmp_path / "out")
        assert result["error"] == "no_svgs"
