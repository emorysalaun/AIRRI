"""adversarial.data — Data loading, manifest parsing, and image I/O."""

from .handler import (
    load_manifest,
    filter_clean_manifest,
    load_dataset_manifest,
    save_dataset_manifest,
    pil_to_dataloader,
    save_composite_image,
)

__all__ = [
    "load_manifest",
    "filter_clean_manifest",
    "load_dataset_manifest",
    "save_dataset_manifest",
    "pil_to_dataloader",
    "save_composite_image",
]
