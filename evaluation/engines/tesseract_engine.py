from pathlib import Path
from typing import Optional

from PIL import Image
import pytesseract


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


def run_tesseract_folder(
    input_dir: Path,
    output_dir: Path,
    tesseract_cmd: Optional[str] = None,
    lang: str = "eng",
    psm: int = 6,
    oem: int = 3,
    timeout: float = 10.0,
) -> int:
    """
    Runs Tesseract OCR on all images in input_dir and writes one .txt file per image
    into output_dir.

    Args:
        input_dir: Folder containing rendered images.
        output_dir: Folder where OCR .txt files will be written.
        tesseract_cmd: Full path to tesseract.exe if it is not in PATH.
        lang: Tesseract language code, usually 'eng'.
        psm: Page segmentation mode.
        oem: OCR engine mode.
        timeout: Max seconds per image before Tesseract is terminated.

    Returns:
        Number of images processed.
    """
    clear_txt_outputs(output_dir)

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    render_images = get_render_images(input_dir)

    for image_path in render_images:
        print(f"  • {image_path.name}")

        config = f"--psm {psm} --oem {oem}"

        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(
                image,
                lang=lang,
                config=config,
                timeout=timeout,
            )
        except RuntimeError as e:
            text = f"[TESSERACT_TIMEOUT] {e}"
        except Exception as e:
            text = f"[TESSERACT_ERROR] {e}"

        output_file = output_dir / f"{image_path.stem}.txt"
        output_file.write_text(text, encoding="utf-8")

    return len(render_images)