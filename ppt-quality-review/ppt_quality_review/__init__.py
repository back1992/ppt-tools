"""ppt-quality-review: quality-review stack for generated slide decks.

Layers:
1. Heuristic description review (4D/5D quality frameworks, density analysis)
2. Static gate (pluggable subprocess adapter, see `gate`)
3. Render-level VLM visual QC (`visual_qc` + `svg_render`, optional extras)
"""

__version__ = "1.0.0"

from . import gate
from .gate import (
    DEFAULT_SCRIPT_NAME,
    DEFAULT_TIMEOUT_S,
    GateResult,
    StaticGate,
    SubprocessStaticGate,
    run_quality_gate,
)

from . import llm
from .llm import VisionReviewer

from . import quality_4d, quality_5d, content_density, image_density
from .quality_4d import (
    DimensionScore,
    QualityAnalyzer4D,
    QualityIssue,
    QualityReport,
    analyze_quality_4d,
)
from .quality_5d import (
    QualityAnalyzer5D,
    VisualQualityChecker,
    analyze_quality_5d,
)
from .content_density import (
    ContentDensityAnalyzer,
    DensityReport,
    Thresholds,
    analyze_content_density,
)
from .image_density import ImageDensityAnalyzer, ImageDensityReport

from . import svg_render, visual_qc
from .visual_qc import (
    KNOWN_ISSUES,
    RUBRIC_VERSION,
    SEVERITY,
    PageReview,
    VisualQCError,
    VisualReview,
    feedback_from_gate,
    feedback_from_review,
    parse_page_review,
    review_rendered_pages,
)
from .svg_render import is_all_background, render_backend_available, render_svg_dir
