"""Mapping between LLM-selected semantic lines and visual line bounding boxes."""

import logging
from dataclasses import dataclass
from renderer.text_renderer import RenderedLine, RenderedImage

logger = logging.getLogger(__name__)


@dataclass
class MatchedRegion:
    """A semantic text excerpt mapped to one or more visual lines in the image."""

    semantic_line: str
    visual_lines: list[RenderedLine]
    union_bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    per_line_gt: str  # Ground truth string combining the texts of the matched lines


def match_semantic_to_visual(
    semantic_lines: list[str], rendered: RenderedImage
) -> list[MatchedRegion]:
    """Map a list of semantic lines to visual lines within a RenderedImage.

    Aligns each semantic line to the corresponding visual lines by tracking
    character ranges in the ground truth text.

    Args:
        semantic_lines: Verbatim substrings of rendered.full_text selected by LLM.
        rendered: The RenderedImage containing visual lines and full text.

    Returns:
        A list of MatchedRegion objects.
    """
    full_text = rendered.full_text
    if not full_text or not rendered.lines:
        return []

    # 1. Map each visual line to its character start and end index in full_text
    line_char_ranges = []
    char_offset = 0
    for vl in rendered.lines:
        start = full_text.find(vl.text, char_offset)
        if start == -1:
            # Fallback to search from beginning if sequential search fails due to wrap artifacts
            start = full_text.find(vl.text)
            if start == -1:
                # If still not found, guess based on current offset
                start = char_offset
        end = start + len(vl.text)
        line_char_ranges.append((start, end, vl))
        char_offset = end

    # 2. Map each semantic line to visual lines by character overlap
    matched_regions = []
    for sem_line in semantic_lines:
        sem_line_stripped = sem_line.strip()
        if not sem_line_stripped:
            continue

        sem_start = full_text.find(sem_line_stripped)
        if sem_start == -1:
            # Try fuzzy search if exact match fails (e.g. minor whitespace differences)
            normalized_sem = "".join(sem_line_stripped.split())
            sem_start = -1
            # Simple sliding window lookup or substring search on normalized text
            for i in range(len(full_text)):
                candidate = "".join(full_text[i : i + len(sem_line_stripped) * 2].split())
                if candidate.startswith(normalized_sem):
                    sem_start = i
                    break

            if sem_start == -1:
                logger.warning(
                    f"Could not locate semantic line in full text: {repr(sem_line_stripped)}"
                )
                continue

        sem_end = sem_start + len(sem_line_stripped)

        # Find all visual lines overlapping with the character range [sem_start, sem_end]
        matched_visual = []
        for ls, le, vl in line_char_ranges:
            # Overlap condition for intervals [ls, le] and [sem_start, sem_end]
            if max(ls, sem_start) < min(le, sem_end):
                matched_visual.append(vl)

        if not matched_visual:
            continue

        # Compute union bounding box
        x1 = min(vl.bbox[0] for vl in matched_visual)
        y1 = min(vl.bbox[1] for vl in matched_visual)
        x2 = max(vl.bbox[2] for vl in matched_visual)
        y2 = max(vl.bbox[3] for vl in matched_visual)
        union_bbox = (x1, y1, x2, y2)

        # Concatenate text of matched visual lines as the per-line ground truth for this region
        per_line_gt = " ".join(vl.text for vl in matched_visual)

        matched_regions.append(
            MatchedRegion(
                semantic_line=sem_line_stripped,
                visual_lines=matched_visual,
                union_bbox=union_bbox,
                per_line_gt=per_line_gt,
            )
        )

    return matched_regions
