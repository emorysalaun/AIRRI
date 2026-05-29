"""Data loading, manifest parsing, and image I/O for the adversarial pipeline."""

import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, TensorDataset


def load_manifest(manifest_path: Path) -> list[dict]:
    """Load and validate the image-to-ground-truth manifest."""
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        if "image_name" not in item or "ground_truth" not in item:
            raise ValueError(
                "Each manifest entry needs 'image_name' and 'ground_truth'"
            )
    return data


def filter_clean_manifest(manifest: list[dict]) -> list[dict]:
    """Keep only manifest entries whose image_name contains 'clean'."""
    return [item for item in manifest if "clean" in item["image_name"].lower()]


def load_dataset_manifest(manifest_path: Path) -> dict:
    """Load prepared dataset manifest containing metadata of generated snippets/images."""
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_dataset_manifest(data: dict, manifest_path: Path):
    """Save prepared dataset manifest containing metadata of generated snippets/images."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def pil_to_dataloader(pil_image: Image.Image, batch_size: int = 1) -> DataLoader:
    """Convert a single PIL image to a DataLoader for attack wrappers.

    Labels are set to 1 (correctly read).
    """
    img = pil_image.convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1)  # HWC -> CHW
    x = tensor.unsqueeze(0)  # Add batch dimension (1, C, H, W)
    y = torch.ones(1, dtype=torch.long)  # true label = 1 (read correctly)
    return DataLoader(TensorDataset(x, y), batch_size=batch_size, shuffle=False)


def save_composite_image(
    composite: np.ndarray, output_dir: Path, image_name: str
):
    """Save a composite image (float32 numpy array [0,1] -> uint8 PNG)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    arr = (np.clip(composite, 0.0, 1.0) * 255).astype(np.uint8)
    pil_img = Image.fromarray(arr)
    pil_img.save(output_dir / image_name)
