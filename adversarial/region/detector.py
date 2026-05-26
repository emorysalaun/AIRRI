"""Visual text-line detection via horizontal projection profiles.

Identifies individual text lines in a rendered document image by
analysing the distribution of dark pixels across rows.  Works for
both monospaced and proportional fonts in single-column layouts.

The detector is **read-only** — it never modifies any pixel in the
source image.
"""

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass
class DetectedLine:
    """A detected visual text line in an image."""

    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2), exclusive end
    line_index: int


def detect_text_lines(
    image: Image.Image,
    threshold: int = 128,
    min_line_height: int = 5,
    padding: int = 2,
) -> list[DetectedLine]:
    """Detect visual text lines using a horizontal projection profile.

    Parameters
    ----------
    image : PIL.Image.Image
        Input image (any mode; converted to RGB internally).
    threshold : int
        Grayscale value below which a pixel is considered "dark" (text).
    min_line_height : int
        Minimum run height (in pixels) to qualify as a text line.
        Anything shorter is discarded as noise.
    padding : int
        Extra pixels added above / below / left / right of each
        detected bounding box.

    Returns
    -------
    list[DetectedLine]
        Detected lines sorted top-to-bottom, with tight bounding boxes.
    """
    arr = np.array(image.convert("RGB"), dtype=np.float64)
    gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    H, W = gray.shape

    binary = gray < threshold  # True where text pixels are

    # -- Horizontal projection: count dark pixels per row ----------------
    proj = binary.sum(axis=1)

    # -- Segment contiguous runs of non-zero rows ------------------------
    in_line = False
    raw_runs: list[tuple[int, int]] = []
    start = 0
    for y in range(H):
        if proj[y] > 0 and not in_line:
            start = y
            in_line = True
        elif proj[y] == 0 and in_line:
            raw_runs.append((start, y))
            in_line = False
    if in_line:
        raw_runs.append((start, H))

    # -- Build DetectedLine objects with column extents ------------------
    lines: list[DetectedLine] = []
    line_idx = 0
    for y_start, y_end in raw_runs:
        if y_end - y_start < min_line_height:
            continue  # too short — likely noise

        # Find column extent for this line
        line_region = binary[y_start:y_end, :]
        col_has_text = line_region.any(axis=0)

        if not col_has_text.any():
            continue  # safety check — no text pixels

        x_start = int(np.argmax(col_has_text))
        x_end = int(W - np.argmax(col_has_text[::-1]))

        # Apply padding (clamped to image bounds)
        y1 = max(0, y_start - padding)
        y2 = min(H, y_end + padding)
        x1 = max(0, x_start - padding)
        x2 = min(W, x_end + padding)

        lines.append(DetectedLine(bbox=(x1, y1, x2, y2), line_index=line_idx))
        line_idx += 1

    return lines
