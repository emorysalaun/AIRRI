from pathlib import Path
from typing import Optional

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText


def run_gotocr_folder(
    input_dir: Path | str,
    output_dir: Path | str,
    model_name: str = "stepfun-ai/GOT-OCR-2.0-hf",
    max_new_tokens: int = 1024,
    device: Optional[str] = None,
) -> int:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Using device: {device}")

    processor = AutoProcessor.from_pretrained(model_name)
    model = AutoModelForImageTextToText.from_pretrained(model_name).to(device)
    model.eval()

    image_paths = sorted(
        p for p in input_dir.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    )

    count = 0

    for image_path in image_paths:
        print(f"  • {image_path.name}")

        try:
            image = Image.open(image_path).convert("RGB")

            inputs = processor(image, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                )

            text = processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()

            out_path = output_dir / f"{image_path.stem}.txt"
            out_path.write_text(text, encoding="utf-8")
            count += 1

        except Exception as e:
            out_path = output_dir / f"{image_path.stem}.txt"
            out_path.write_text("", encoding="utf-8")
            print(f"    Error on {image_path.name}: {e}")

    return count