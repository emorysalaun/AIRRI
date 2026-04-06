from pathlib import Path

from PIL import Image, ImageOps
import numpy as np
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


def crop_whitespace(
    image: Image.Image,
    bg_threshold: int = 245,
    padding: int = 12,
) -> Image.Image:
    gray = image.convert("L")
    mask = gray.point(lambda x: 255 if x < bg_threshold else 0)
    bbox = mask.getbbox()

    if bbox is None:
        return image

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)

    return image.crop((left, top, right, bottom))


def resize_if_large(image: Image.Image, max_width: int = 1600) -> Image.Image:
    if image.width <= max_width:
        return image

    scale = max_width / image.width
    new_width = int(image.width * scale)
    new_height = int(image.height * scale)

    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def preprocess_image(image_path: Path) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    image = crop_whitespace(image)
    image = resize_if_large(image)
    return image


def split_into_lines(
    image: Image.Image,
    threshold: int = 245,
    min_line_height: int = 8,
):
    gray = image.convert("L")
    arr = np.array(gray)

    ink = arr < threshold
    row_sum = ink.sum(axis=1)

    lines = []
    in_line = False
    start = 0

    for y, val in enumerate(row_sum):
        if val > 0 and not in_line:
            in_line = True
            start = y
        elif val == 0 and in_line:
            end = y
            if end - start > min_line_height:
                lines.append((start, end))
            in_line = False

    if in_line:
        end = len(row_sum)
        if end - start > min_line_height:
            lines.append((start, end))

    line_images = []
    for top, bottom in lines:
        line_img = image.crop((0, top, image.width, bottom))
        line_images.append(line_img)

    return line_images


def crop_line_horizontally(
    line_img: Image.Image,
    threshold: int = 245,
    padding_x: int = 16,
    padding_y: int = 8,
) -> Image.Image:
    gray = line_img.convert("L")
    arr = np.array(gray)

    ink = arr < threshold
    coords = np.argwhere(ink)

    if coords.size == 0:
        return line_img

    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)

    left = max(0, x_min - padding_x)
    top = max(0, y_min - padding_y)
    right = min(line_img.width, x_max + 1 + padding_x)
    bottom = min(line_img.height, y_max + 1 + padding_y)

    return line_img.crop((left, top, right, bottom))


def upscale_line(
    line_img: Image.Image,
    target_height: int = 64,
) -> Image.Image:
    if line_img.height >= target_height:
        return line_img

    scale = target_height / line_img.height
    new_width = max(1, int(line_img.width * scale))
    new_height = target_height

    return line_img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def add_white_border(
    image: Image.Image,
    border: int = 12,
) -> Image.Image:
    return ImageOps.expand(image, border=border, fill="white")


def prepare_line_for_trocr(line_img: Image.Image) -> Image.Image:
    line_img = crop_line_horizontally(line_img)
    line_img = upscale_line(line_img, target_height=64)
    line_img = add_white_border(line_img, border=12)
    return line_img.convert("RGB")


def run_trocr_folder(
    input_dir: Path,
    output_dir: Path,
    model_name: str = "microsoft/trocr-base-printed",
    device: str | None = None,
    max_new_tokens: int = 128,
) -> int:
    clear_txt_outputs(output_dir)

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    model.to(device)
    model.eval()

    render_images = get_render_images(input_dir)

    debug_dir = output_dir / "_debug_lines"
    debug_dir.mkdir(parents=True, exist_ok=True)

    for image_path in render_images:
        print(f"  • {image_path.name}")

        try:
            image = preprocess_image(image_path)

            line_images = split_into_lines(image)
            print(f"    detected {len(line_images)} lines")

            lines_text = []

            for i, line_img in enumerate(line_images):
                line_img = prepare_line_for_trocr(line_img)

                # debug save
                line_img.save(debug_dir / f"{image_path.stem}_line_{i+1}.png")

                pixel_values = processor(images=line_img, return_tensors="pt").pixel_values
                pixel_values = pixel_values.to(device)

                with torch.no_grad():
                    generated_ids = model.generate(
                        pixel_values,
                        max_new_tokens=max_new_tokens,
                        num_beams=6,
                        early_stopping=True,
                        no_repeat_ngram_size=3,
                    )

                line_text = processor.batch_decode(
                    generated_ids,
                    skip_special_tokens=True
                )[0].strip()

                lines_text.append(line_text)

            text = "\n".join(lines_text)

        except Exception as e:
            text = f"[TROCR_ERROR] {e}"

        output_file = output_dir / f"{image_path.stem}.txt"
        output_file.write_text(text, encoding="utf-8")

    return len(render_images)