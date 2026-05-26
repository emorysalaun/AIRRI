"""Hard-mask compositing for adversarial region stitching.

Replaces selected bounding-box regions in a clean image with adversarial
crops while preserving all other pixels exactly.

Mathematical guarantee (hard mask):
    I_composite(y, x, c) = I_adv_crop(y-y1, x-x1, c)   if (x1 ≤ x < x2) ∧ (y1 ≤ y < y2)
    I_composite(y, x, c) = I_clean(y, x, c)             otherwise
"""

import numpy as np


def stitch_adversarial(
    clean_image: np.ndarray,
    adv_crop: np.ndarray,
    bbox: tuple[int, int, int, int],
) -> np.ndarray:
    """Replace the *bbox* region of *clean_image* with *adv_crop* (hard mask).

    Parameters
    ----------
    clean_image : np.ndarray
        Original clean image, shape ``(H, W, 3)``, float32, values in [0, 1].
    adv_crop : np.ndarray
        Adversarial crop, shape ``(h, w, 3)``, float32, values in [0, 1].
    bbox : tuple
        ``(x1, y1, x2, y2)`` — the region in *clean_image* that *adv_crop*
        replaces.  Uses Python-slice convention (exclusive end).

    Returns
    -------
    np.ndarray
        Composite image, same shape and dtype as *clean_image*.
    """
    x1, y1, x2, y2 = bbox
    H, W = clean_image.shape[:2]

    # Clamp to image bounds
    x1c = max(0, x1)
    y1c = max(0, y1)
    x2c = min(W, x2)
    y2c = min(H, y2)

    expected_h = y2c - y1c
    expected_w = x2c - x1c
    crop_h, crop_w = adv_crop.shape[:2]

    if crop_h != expected_h or crop_w != expected_w:
        raise ValueError(
            f"Adversarial crop size ({crop_h}, {crop_w}) does not match "
            f"clamped bbox size ({expected_h}, {expected_w}) for bbox "
            f"({x1}, {y1}, {x2}, {y2}) in image ({H}, {W})."
        )

    composite = clean_image.copy()
    composite[y1c:y2c, x1c:x2c, :] = adv_crop
    return np.clip(composite, 0.0, 1.0)


def stitch_multi_region(
    clean_image: np.ndarray,
    adv_crops: list[np.ndarray],
    bboxes: list[tuple[int, int, int, int]],
) -> np.ndarray:
    """Stitch multiple adversarial crops into a clean image.

    Regions are applied sequentially.  For non-overlapping bounding
    boxes (the normal case for text lines in single-column documents)
    the order does not matter.

    Parameters
    ----------
    clean_image : np.ndarray
        Original clean image, shape ``(H, W, 3)``, float32, [0, 1].
    adv_crops : list[np.ndarray]
        One adversarial crop per selected line.
    bboxes : list[tuple]
        One ``(x1, y1, x2, y2)`` per crop, same order as *adv_crops*.

    Returns
    -------
    np.ndarray
        Composite image with all adversarial regions stitched in.
    """
    if len(adv_crops) != len(bboxes):
        raise ValueError(
            f"Got {len(adv_crops)} crops but {len(bboxes)} bboxes."
        )

    composite = clean_image.copy()
    for crop, bbox in zip(adv_crops, bboxes):
        composite = stitch_adversarial(composite, crop, bbox)
    return composite
