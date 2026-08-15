"""
Image Density Analysis for PPT presentations.

Determines when a presentation needs AI-generated images based on
image-to-slide ratio and minimum thresholds.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ImageDensityReport:
    """Report on image density in a presentation."""
    total_slides: int
    image_count: int
    content_slides: int
    image_to_slide_ratio: float
    needs_ai_images: bool
    deficit: int  # how many images needed to reach threshold


class ImageDensityAnalyzer:
    """Analyze presentation image density and determine if AI images are needed."""
    
    # Thresholds
    MIN_IMAGES_PER_SLIDE_RATIO = 0.3  # At least 1 image per 3 slides
    MIN_TOTAL_IMAGES = 2              # At least 2 images total
    MAX_AI_IMAGES = 5                 # Cap AI generation at 5
    
    def analyze(self, slide_count: int, image_count: int) -> ImageDensityReport:
        """
        Determine if AI images are needed based on density thresholds.
        
        Args:
            slide_count: Total number of slides in presentation
            image_count: Number of images already in presentation
        
        Returns:
            ImageDensityReport with needs_ai_images=True if below threshold
        """
        if slide_count <= 0:
            return ImageDensityReport(
                total_slides=0,
                image_count=0,
                content_slides=0,
                image_to_slide_ratio=0.0,
                needs_ai_images=False,
                deficit=0,
            )
        
        ratio = image_count / slide_count
        
        # Calculate target: max of minimum total or ratio-based target
        target_images = max(
            self.MIN_TOTAL_IMAGES,
            int(slide_count * self.MIN_IMAGES_PER_SLIDE_RATIO)
        )
        
        # Calculate deficit (how many more images needed)
        deficit = max(0, target_images - image_count)
        
        # Cap at MAX_AI_IMAGES
        capped_deficit = min(deficit, self.MAX_AI_IMAGES)
        
        # Estimate content slides (exclude title and summary)
        content_slides = max(0, slide_count - 2)
        
        needs_ai = capped_deficit > 0
        
        logger.debug(
            f"Image density: {image_count}/{slide_count} slides "
            f"(ratio={ratio:.2f}, target={target_images}, deficit={capped_deficit})"
        )
        
        return ImageDensityReport(
            total_slides=slide_count,
            image_count=image_count,
            content_slides=content_slides,
            image_to_slide_ratio=ratio,
            needs_ai_images=needs_ai,
            deficit=capped_deficit,
        )
