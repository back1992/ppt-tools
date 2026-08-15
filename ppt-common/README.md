# ppt-common

Shared utilities for slide-deck generation packages — published so
downstream packages (e.g. `ppt-quality-review`) and external projects can
depend on one copy.

Zero core dependencies; optional extras for the LLM client and agents.

## Install

```bash
pip install ppt-common            # text utilities only
pip install "ppt-common[llm]"     # + OpenAI-compatible LLM client
pip install "ppt-common[agents]"  # + pydantic-ai agent helpers
```

## Modules

| Module | Contents |
|---|---|
| `ppt_common.text` | CJK detection (`is_cjk`, `is_cjk_char`, ...), sentence splitting, PDF line merging, page cleaning, section-header detection |
| `ppt_common.text_metrics` | CJK-aware rendered-width estimation, `fit_font_size`, greedy line wrapping |
| `ppt_common.pdf_structure` / `ppt_common.content_splitter` | PDF structure helpers |
| `ppt_common.llm` (`[llm]` extra) | `LLMClient` for any OpenAI-compatible endpoint, `parse_llm_json` |
| `ppt_common.agents` (`[agents]` extra) | pydantic-ai agent utilities |

## LLM client configuration

`LLMClient` works with any OpenAI-compatible endpoint. Configuration falls
back through environment variables:

| Parameter | Explicit arg | Env vars (first match wins) |
|---|---|---|
| API key | `api_key=` | `DASHSCOPE_API_KEY`, `LLM_API_KEY` |
| Base URL | `base_url=` | `DASHSCOPE_BASE_URL`, `LLM_BASE_URL` |
| Model | `model=` | `DASHSCOPE_MODEL`, `LLM_MODEL` |

```python
from ppt_common.llm import LLMClient

client = LLMClient()                      # reads env vars
reply = client.chat("Summarize: ...")     # or pass api_key=/base_url=/model=
```

## Development

Tests live in `tests/` — run with `pytest tests/`. `text.py` and
`text_metrics.py` carry a mutmut mutation-audit pilot (100% kill rate).
