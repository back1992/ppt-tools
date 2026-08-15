# ppt-tools

Standalone tool packages for slide-deck generation.

| Package | PyPI | Description |
|---|---|---|
| `ppt-common` | [pypi.org/project/ppt-common](https://pypi.org/project/ppt-common/) | Shared utilities: CJK text handling, text metrics, PDF line merging, LLM client |
| `ppt-quality-review` | [pypi.org/project/ppt-quality-review](https://pypi.org/project/ppt-quality-review/) | Quality-review stack for generated slide decks: 4D/5D heuristics, pluggable static gate, render-level VLM visual QC |

```bash
pip install ppt-common
pip install "ppt-quality-review[llm,visual]"
```

Each package has its own README, tests, and examples. Releases are published
from this repository via PyPI trusted publishing (OIDC, tag-triggered — see
`.github/workflows/publish.yml`).
