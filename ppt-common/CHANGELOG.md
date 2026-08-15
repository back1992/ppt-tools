# Changelog

All notable changes to `ppt-common` are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- `LLMClient` now constructs the underlying OpenAI client with
  `max_retries=0`. The SDK's internal retries (default 2) silently re-ran
  stalled reads, tripling the wall time of a hung-gateway call before
  `_complete`'s own logged/backoff retry policy saw the error
  (~18 min -> ~6 min per failed call at `timeout=180`). Retry policy is
  owned by `_complete`.

## [1.0.1] - 2026-08-15

### Changed

- Added `project.urls` metadata (Homepage / Repository / Issues) pointing
  at the public tools repository `back1992/ppt-tools`. No functional
  changes.

### Note

- The `LLMClient` `max_retries=0` fix listed under [Unreleased] was
  already included in the 1.0.0 release artifacts.

## [1.0.0] - 2026-08-14

First public release. Previously an internal package, in production use
by slide-deck generation pipelines and by `ppt-quality-review`.

### Included

- CJK-aware text utilities (`ppt_common.text`): CJK detection, sentence
  splitting, PDF line merging, page cleaning, section-header detection.
- Rendered-text metrics (`ppt_common.text_metrics`): CJK-aware width
  estimation, font-size fitting, greedy wrapping.
- PDF structure helpers (`ppt_common.pdf_structure`, `ppt_common.content_splitter`).
- OpenAI-compatible LLM client (`ppt_common.llm`, `[llm]` extra): any
  OpenAI-compatible endpoint via explicit args or `LLM_API_KEY` /
  `LLM_BASE_URL` / `LLM_MODEL` env vars (DashScope fallbacks included).
- pydantic-ai agent helpers (`ppt_common.agents`, `[agents]` extra).
