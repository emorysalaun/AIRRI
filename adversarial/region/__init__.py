"""adversarial.region — Region matching and stitching."""

from .stitcher import stitch_adversarial, stitch_multi_region
from .matcher import MatchedRegion, match_semantic_to_visual

__all__ = [
    "MatchedRegion",
    "match_semantic_to_visual",
    "stitch_adversarial",
    "stitch_multi_region",
]
