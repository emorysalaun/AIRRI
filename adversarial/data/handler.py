"""Data loading, manifest parsing, and image I/O for the adversarial pipeline."""

import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, TensorDataset

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


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


def get_render_images(input_dir: Path) -> list[Path]:
    """Return sorted list of image files in the given directory."""
    return sorted(
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def images_to_dataloader(image_paths: list[Path], batch_size: int = 1) -> DataLoader:
    """Load render images into a DataLoader for attack wrappers.

    Labels are set to 1 (correctly read) so untargeted attacks
    try to flip the prediction to 0 (misread).
    """
    tensors = []
    for p in image_paths:
        img = Image.open(p).convert("RGB")
        arr = np.array(img, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr).permute(2, 0, 1)  # HWC -> CHW
        tensors.append(tensor)

    x = torch.stack(tensors)
    y = torch.ones(len(tensors), dtype=torch.long)  # true label = 1 (read correctly)
    return DataLoader(TensorDataset(x, y), batch_size=batch_size, shuffle=False)


def save_adversarial_images(
    adv_loader: DataLoader, output_dir: Path, original_names: list[str]
):
    """Save adversarial images from a DataLoader to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    idx = 0
    for batch_x, _ in adv_loader:
        for i in range(batch_x.shape[0]):
            if idx >= len(original_names):
                break
            img_tensor = batch_x[i]
            arr = (img_tensor.detach().cpu().clamp(0, 1) * 255).byte()
            arr = arr.permute(1, 2, 0).numpy()
            if arr.shape[2] == 1:
                arr = arr.squeeze(2)
            pil_img = Image.fromarray(arr)
            pil_img.save(output_dir / original_names[idx])
            idx += 1
