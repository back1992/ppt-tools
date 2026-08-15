# Changelog

All notable changes to `ppt-quality-review` are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-08-15

### Changed

- Added `project.urls` metadata (Homepage / Repository / Issues) pointing
  at the public tools repository `back1992/ppt-tools`. No functional
  changes.

## [1.0.0] - 2026-08-14

First public release. Previously an internal package, extracted from a
slide-deck generation pipeline.

### Included

- Layer 1 — heuristic description review: 4D/5D quality frameworks
  (`quality_4d`, `quality_5d`), CJK-aware content-density and
  image-density analyzers (`content_density`, `image_density`).
- Layer 2 — pluggable static gate (`gate`): subprocess adapter for an
  external SVG checker script (exit 0 = pass).
- Layer 3 — render-level VLM visual QC (`visual_qc` + `svg_render`,
  `[visual]` extra): SVG→PNG via Playwright, per-page vision-LLM review
  with blocking/cosmetic severity tiers and re-authoring feedback.
- `examples/heuristic_review.py`: offline quickstart (no API key needed).
