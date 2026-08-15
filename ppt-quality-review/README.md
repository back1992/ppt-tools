# ppt-quality-review

Quality-review stack for generated slide decks. Three layers:

1. **Heuristic description review** — 4D/5D quality frameworks (Structure,
   Density, CRAP design principles, Scene, Visual richness) scoring slide
   description dicts, plus CJK-aware content-density and image-density
   analyzers.
2. **Static gate** — pluggable subprocess adapter for an external SVG checker
   script (exit 0 = pass).
3. **Render-level VLM visual QC** — render slide SVGs to PNGs (Playwright),
   review each page with a vision LLM (blocking vs cosmetic severity tiers),
   and produce re-authoring feedback strings.

## Install

```bash
pip install ppt-quality-review
```

Optional extras (as declared in `pyproject.toml`):

- `[llm]` — `openai>=1.0.0` + `httpx>=0.24.0`, for the default VLM client
  (`ppt_common.llm.LLMClient`, OpenAI-compatible).
- `[visual]` — `playwright>=1.40` + `pillow>=10.0`, for the SVG→PNG renderer
  (`ppt_quality_review.svg_render`).
- `[dev]` — `pytest>=7.0`, for working on the package itself.

Layer 1 (heuristics) and Layer 2 (static gate) need no extras beyond the
`ppt-common` base dependency.

## Quickstart

A runnable offline version of this example (no API key needed) ships in
`examples/heuristic_review.py`.

```python
from ppt_quality_review import analyze_quality_5d

slides = [
    {"type": "content", "title": "Intro",
     "bullets": ["Point one", "Point two"], "image_path": "a.png"},
    {"type": "content", "title": "Details",
     "bullets": ["Fact A", "Fact B"], "image_path": "b.png"},
]
report = analyze_quality_5d(slides)
print(report.overall_score, [str(i) for i in report.all_issues])
```

### Bring your own VLM client (Layer 3)

Any object with one method satisfies `VisionReviewer`:

```python
from ppt_quality_review import review_rendered_pages
from ppt_quality_review.svg_render import render_svg_dir

class MyReviewer:
    def chat_with_images(self, user_prompt, image_paths, *, model=""):
        ...  # call your VLM of choice, return the raw text response

render = render_svg_dir(svg_dir, out_dir)          # needs [visual] extra
review = review_rendered_pages(render["pages"], page_briefs,
                               client=MyReviewer())
print(review.blocking)  # [(page_index, issue), ...]
```

The default client (`ppt_common.llm.LLMClient`, OpenAI-compatible/DashScope)
is used when `client=None`; it needs the `[llm]` extra and
`DASHSCOPE_API_KEY`/`LLM_API_KEY` env vars. Any OpenAI-compatible endpoint
works: `LLMClient` also honors `LLM_BASE_URL` / `LLM_MODEL` (with
`DASHSCOPE_BASE_URL` / `DASHSCOPE_MODEL` fallbacks), or explicit
`api_key=` / `base_url=` / `model=` arguments.

### Static gate

```python
from ppt_quality_review import SubprocessStaticGate, run_quality_gate

gate = SubprocessStaticGate(script_dir="/path/to/checker/scripts")
result = gate.run(svg_project_dir)   # GateResult(passed, exit_code, output)
```

Unconfigured gates soft-pass (`exit_code=-1`); host projects pin their
own checker via the `script_dir` arg.

**Unavailable ≠ failure.** When `script_dir` is configured but the checker
script itself is missing from it, the gate also soft-passes with
`exit_code=-1` and logs a WARNING — a missing checker never blocks a build.
In practice this only triggers on a corrupted or partial checkout of
the checker scripts.

## Integration

The three layers compose into an author→gate→render→review→re-author
loop; the host pipeline decides when to invoke each layer. Layers 1 and 2
are offline; Layer 3 needs the `[llm]` and `[visual]` extras.
