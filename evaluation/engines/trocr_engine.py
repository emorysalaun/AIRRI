from pathlib import Path

from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def get_render_images(input_dir: Path) -> list[Path]:
    return sorted(
        [
            p for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]
    )


def clear_txt_outputs(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for f in output_dir.glob("*.txt"):
        f.unlink()


def run_trocr_folder(
    input_dir: Path,
    output_dir: Path,
    model_name: str = "microsoft/trocr-base-printed",
    device: str | None = None,
    max_new_tokens: int = 256,
) -> int:
    """
    Runs TrOCR on all images in input_dir and writes one .txt file per image
    into output_dir.

    Args:
        input_dir: Folder containing rendered images.
        output_dir: Folder where OCR .txt files will be written.
        model_name: Hugging Face model checkpoint.
        device: 'cuda' or 'cpu'. If None, auto-detect.
        max_new_tokens: Max decoded text length.

    Returns:
        Number of images processed.
    """
    clear_txt_outputs(output_dir)

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    model.to(device)
    model.eval()

    render_images = get_render_images(input_dir)

    for image_path in render_images:
        print(f"  • {image_path.name}")

        try:
            image = Image.open(image_path).convert("RGB")

            pixel_values = processor(images=image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(device)

            with torch.no_grad():
                generated_ids = model.generate(
                    pixel_values,
                    max_new_tokens=max_new_tokens,
                )

            text = processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]

        except Exception as e:
            text = f"[TROCR_ERROR] {e}"

        output_file = output_dir / f"{image_path.stem}.txt"
        output_file.write_text(text, encoding="utf-8")

    return len(render_images)