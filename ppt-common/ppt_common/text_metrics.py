"""
Shared text-width estimation, font-size fitting and line wrapping.

Single source of truth for typography metrics. The per-character width
model is em-based so authoring-time estimates and gate-time estimates
stay on the same scale.

Units: ``font_size``/widths are unitless-consistent — pass px, get px;
pass pt, get pt (the model is em-based).

Usage:
    from ppt_common.text_metrics import estimate_text_width, fit_font_size, wrap_text
"""

from __future__ import annotations

import math
from functools import lru_cache

from ppt_common.text import is_cjk_char

# ─── Per-character advance widths (em) ──────────────────────────────────
CJK_EM = 1.0          # CJK ideographs + CJK punctuation
SPACE_EM = 0.3
WIDE_LATIN_EM = 0.75  # mMwWOQ%
NARROW_LATIN_EM = 0.3 # iIlj!|
DIGIT_EM = 0.55       # tabular digits
DEFAULT_EM = 0.55     # everything else

BOLD_FACTOR = 1.05
# Safety multiplier for authoring-time wrapping so pre-wrapped lines
# survive the gate-time width check.
DEFAULT_HEADROOM = 1.06

_WIDE_LATIN = frozenset("mMwWOQ%")
_NARROW_LATIN = frozenset("iIlj!|")

DEFAULT_MIN_SIZE = 8.0
DEFAULT_MAX_SIZE = 44.0
DEFAULT_LINE_HEIGHT = 1.2


def char_width_em(ch: str) -> float:
    """Advance width of one character in em (spec table above)."""
    if is_cjk_char(ch):
        return CJK_EM
    if ch == " ":
        return SPACE_EM
    if ch in _WIDE_LATIN:
        return WIDE_LATIN_EM
    if ch in _NARROW_LATIN:
        return NARROW_LATIN_EM
    if ch.isdigit():
        return DIGIT_EM
    return DEFAULT_EM


def estimate_text_width(
    text: str,
    font_size: float,
    *,
    bold: bool = False,
    headroom: float = 1.0,
) -> float:
    """Estimated rendered width of ``text`` in the same unit as ``font_size``."""
    em = sum(char_width_em(ch) for ch in text)
    if bold:
        em *= BOLD_FACTOR
    return em * font_size * headroom


def estimate_lines(
    text: str,
    font_size: float,
    box_width: float,
    *,
    bold: bool = False,
    headroom: float = 1.0,
) -> int:
    """Lines needed when ``text`` wraps into ``box_width`` (explicit \\n respected)."""
    if box_width <= 0:
        return 0
    total = 0
    for line in text.split("\n"):
        width = estimate_text_width(line, font_size, bold=bold, headroom=headroom)
        total += max(1, math.ceil(width / box_width)) if line else 1
    return total


def fits(
    text: str,
    font_size: float,
    box_width: float,
    box_height: float,
    *,
    line_height: float = DEFAULT_LINE_HEIGHT,
    bold: bool = False,
) -> bool:
    """True when wrapped text at ``font_size`` fits the box height."""
    if box_width <= 0 or font_size <= 0:
        return False
    lines = estimate_lines(text, font_size, box_width, bold=bold)
    # box_height <= 0 needs no separate guard: LHS is positive here.
    return lines * font_size * line_height <= box_height


def fit_font_size(
    text: str,
    box_width: float,
    box_height: float,
    *,
    min_size: float = DEFAULT_MIN_SIZE,
    max_size: float = DEFAULT_MAX_SIZE,
    line_height: float = DEFAULT_LINE_HEIGHT,
    bold: bool = False,
) -> float:
    """Largest font size (binary search, 0.25 precision) that fits the box.

    Returns ``min_size`` when even the minimum overflows (caller may then
    truncate); ``max_size`` when the text fits without shrinking.
    """
    if not text:
        return max_size
    fit = dict(line_height=line_height, bold=bold)
    if fits(text, max_size, box_width, box_height, **fit):
        return max_size
    if not fits(text, min_size, box_width, box_height, **fit):
        return min_size
    lo, hi = min_size, max_size
    while hi - lo > 0.25:
        mid = (lo + hi) / 2
        if fits(text, mid, box_width, box_height, **fit):
            lo = mid
        else:
            hi = mid
    return lo


def wrap_text(
    text: str,
    font_size: float,
    max_width: float,
    *,
    bold: bool = False,
    headroom: float = DEFAULT_HEADROOM,
) -> list[str]:
    """Greedy wrap: CJK breaks per character, Latin per word.

    ``headroom`` shrinks the usable width so estimates survive renderer
    variance.
    """
    usable = max_width / headroom if headroom else max_width
    out: list[str] = []
    for raw_line in text.split("\n"):
        units = _wrap_units(raw_line)
        current = ""
        current_w = 0.0
        for unit in units:
            w = estimate_text_width(unit, font_size, bold=bold)
            if current and current_w + w > usable:
                out.append(current.rstrip())
                current, current_w = unit.lstrip(" "), w
            else:
                current += unit
                current_w += w
        out.append(current)
    return out


def _wrap_units(line: str) -> list[str]:
    """Split a line into atomic wrap units (CJK chars / Latin words+space)."""
    units: list[str] = []
    buf = ""
    for ch in line:
        if is_cjk_char(ch):
            if buf:
                units.append(buf)
                buf = ""
            units.append(ch)
        elif ch == " ":
            buf += ch
            if any(not c.isspace() for c in buf) and buf.strip():  # pragma: no mutate (equivalent conjuncts: both mean 'buf has a non-space')
                # space terminates a latin word; keep it attached for wrapping
                units.append(buf)
                buf = ""
        else:
            buf += ch
    if buf:
        units.append(buf)
    return units


@lru_cache(maxsize=64)
def _load_font(font_path: str, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(font_path, size=size)


def measure_text_width(text: str, font_size: float, font_path: str) -> float | None:
    """Ground-truth width via PIL FreeType (px at ``font_size``), or None.

    Intended for tests/calibration only — the runtime path stays
    font-file-free.
    """
    try:
        font = _load_font(str(font_path), int(round(font_size)))
    except Exception:
        return None
    try:
        return float(font.getlength(text))
    except Exception:
        return None
