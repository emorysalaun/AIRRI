"""adversarial.region — Region detection, matching, and stitching."""

from .detector import DetectedLine, detect_text_lines
from .stitcher import stitch_adversarial, stitch_multi_region
from .matcher import MatchedRegion, match_semantic_to_visual

__all__ = [
    "DetectedLine",
    "detect_text_lines",
    "MatchedRegion",
    "match_semantic_to_visual",
    "stitch_adversarial",
    "stitch_multi_region",
]
