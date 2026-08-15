"""Thin SVG -> PNG renderer for the render-level visual QC loop.

The authored SVGs are expected to be self-contained (no icons/<image>/
external CSS), so a bare Chromium ``set_content`` render is equivalent
to a full live-preview pipeline.

Requires the optional extra: ``pip install playwright && playwright install
chromium``. Degrades gracefully — :func:`render_svg_dir` reports
``backend_missing``/``launch_failed`` instead of raising.
"""

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

VIEWPORT = (1280, 720)
# Histogram threshold: a page counts as
# blank when one 4-bit-quantized color bucket holds >= 99% of pixels.
ALL_BG_THRESHOLD = 0.99

_backend_available: bool | None = None


def reset_backend_probe_cache() -> None:
    """Test hook: clear the cached playwright probe result."""
    global _backend_available
    _backend_available = None


def render_backend_available() -> bool:
    """True when playwright + chromium can actually launch (cached)."""
    global _backend_available
    if _backend_available is None:
        _backend_available = _probe()
    return _backend_available


def _probe() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.info("visual QC render backend missing: playwright not installed")
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception as exc:
        logger.info("visual QC render backend unavailable: %s", exc)
        return False


def is_all_background(png_path: Path | str) -> bool:
    """Blank-render guard: dominant 4-bit color bucket >= ALL_BG_THRESHOLD."""
    from PIL import Image

    img = Image.open(str(png_path)).convert("RGB").resize((64, 36))
    counts: dict[tuple[int, int, int], int] = {}
    for r, g, b in img.getdata():
        key = (r >> 4, g >> 4, b >> 4)
        counts[key] = counts.get(key, 0) + 1
    total = 64 * 36
    return max(counts.values()) / total >= ALL_BG_THRESHOLD


def render_svg_dir(svg_dir: Path | str, out_dir: Path | str) -> dict:
    """Render ``svg_output/*.svg`` to 1280x720 PNGs via Chromium.

    Returns ``{"ok": bool, "pages": [{"page", "ok", "path", "sha256",
    "all_background", "error"}], "error": str | None}``. Never raises.
    """
    svg_dir = Path(svg_dir)
    out_dir = Path(out_dir)
    svgs = sorted(svg_dir.glob("*.svg"))
    if not svgs:
        return {"ok": False, "pages": [], "error": "no_svgs"}
    if not render_backend_available():
        return {"ok": False, "pages": [], "error": "backend_missing"}

    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[dict] = []
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                context = browser.new_context(
                    viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]})
                for svg_path in svgs:
                    rec: dict = {"page": svg_path.name, "ok": False}
                    try:
                        page = context.new_page()
                        page.set_content(svg_path.read_text(encoding="utf-8"))
                        # one frame so font/text shaping settles
                        page.wait_for_timeout(100)
                        out_path = out_dir / f"{svg_path.stem}.png"
                        page.screenshot(path=str(out_path), type="png")
                        page.close()
                        digest = hashlib.sha256(
                            out_path.read_bytes()).hexdigest()
                        rec.update(
                            ok=True,
                            path=str(out_path),
                            sha256=digest,
                            all_background=is_all_background(out_path),
                        )
                    except Exception as exc:  # best-effort per page
                        rec["error"] = f"{type(exc).__name__}: {exc}"
                    pages.append(rec)
            finally:
                browser.close()
        return {"ok": True, "pages": pages, "error": None}
    except Exception as exc:
        logger.warning("visual QC render failed: %s", exc)
        return {"ok": False, "pages": pages, "error": f"launch_failed: {exc}"}
