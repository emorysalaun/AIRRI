"""adversarial.data — Data loading, manifest parsing, and image I/O."""

from .handler import (
    load_manifest,
    filter_clean_manifest,
    get_render_images,
    images_to_dataloader,
    save_adversarial_images,
)

__all__ = [
    "load_manifest",
    "filter_clean_manifest",
    "get_render_images",
    "images_to_dataloader",
    "save_adversarial_images",
]
