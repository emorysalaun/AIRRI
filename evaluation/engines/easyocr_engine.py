from pathlib import Path
from typing import Iterable
import easyocr


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


def sort_reading_order(results: Iterable, line_threshold: int = 25) -> list[str]:
    """
    Sort EasyOCR results into a more stable top-to-bottom, left-to-right reading order.
    Expects each item to be: (bbox, text, confidence)
    """
    boxes = []

    for bbox, text, conf in results:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]

        cx = sum(xs) / 4
        cy = sum(ys) / 4

        boxes.append({"x": cx, "y": cy, "text": text})

    lines = []

    for box in boxes:
        placed = False

        for line in lines:
            avg_y = sum(b["y"] for b in line) / len(line)
            if abs(box["y"] - avg_y) < line_threshold:
                line.append(box)
                placed = True
                break

        if not placed:
            lines.append([box])

    lines.sort(key=lambda line: sum(b["y"] for b in line) / len(line))

    ordered_text = []
    for line in lines:
        line.sort(key=lambda b: b["x"])
        ordered_text.extend([b["text"] for b in line])

    return ordered_text


def run_easyocr_folder(
    input_dir: Path,
    output_dir: Path,
    languages: list[str] | None = None,
    gpu: bool = False,
    paragraph: bool = True,
    use_sorted_reading_order: bool = False,
    line_threshold: int = 25,
) -> int:
    """
    Runs EasyOCR on all images in input_dir and writes one .txt file per image into output_dir.

    Returns:
        Number of images processed.
    """
    if languages is None:
        languages = ["en"]

    clear_txt_outputs(output_dir)

    reader = easyocr.Reader(languages, gpu=gpu)
    render_images = get_render_images(input_dir)

    for image_path in render_images:
        print(f"  • {image_path.name}")

        results = reader.readtext(str(image_path), paragraph=paragraph)

        if use_sorted_reading_order and not paragraph:
            texts = sort_reading_order(results, line_threshold=line_threshold)
        else:
            texts = [r[1] for r in results]

        ocr_joined = " ".join(texts)

        output_file = output_dir / f"{image_path.stem}.txt"
        output_file.write_text(ocr_joined, encoding="utf-8")

    return len(render_images)