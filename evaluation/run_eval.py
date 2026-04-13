from pathlib import Path
import json
import warnings

from engines.easyocr_engine import run_easyocr_folder
from engines.tesseract_engine import run_tesseract_folder
from engines.gotocr_engine import run_gotocr_folder

from score import evaluate_ocr_folder_with_manifest


warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RENDERS_DIR = DATA_DIR / "renders"
MANIFEST_PATH = DATA_DIR / "manifest.json"

RESULTS_DIR = BASE_DIR / "results"

EASYOCR_RESULTS_DIR = RESULTS_DIR / "easyocr"
TESSERACT_RESULTS_DIR = RESULTS_DIR / "tesseract"
GOTOCR_RESULTS_DIR = RESULTS_DIR / "gotocr"


def load_manifest(manifest_path: Path) -> list[dict]:
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("manifest.json must contain a list of entries")

    for item in data:
        if "image_name" not in item or "ground_truth" not in item:
            raise ValueError("Each manifest entry must have 'image_name' and 'ground_truth'")

    return data


def print_engine_results(results_dir: Path, scores: dict[str, float], engine_name: str) -> None:
    print(f"\n--- {engine_name} Results ---")

    for name, acc in scores.items():
        text_path = results_dir / name
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else "[Missing OCR output file]"

        print(f"\n{name}")
        print("-" * 60)
        print(text)
        print(f"\nAccuracy → {acc:.2f}%\n")

    if not scores:
        print("No results found.")
        return

    print("\nSummary")
    print("-" * 39)

    values = list(scores.values())
    avg = sum(values) / len(values)

    best_file = max(scores, key=scores.get)
    worst_file = min(scores, key=scores.get)

    print(f"Images evaluated : {len(scores)}")
    print(f"Average accuracy : {avg:.2f}%")
    print(f"Best result      : {best_file} ({scores[best_file]:.2f}%)")
    print(f"Worst result     : {worst_file} ({scores[worst_file]:.2f}%)")


def main() -> None:
    manifest = load_manifest(MANIFEST_PATH)

    print("\n=== AIRRI Evaluation Pipeline ===\n")

    print("[1/6] EasyOCR Inference")
    easyocr_count = run_easyocr_folder(
        input_dir=RENDERS_DIR,
        output_dir=EASYOCR_RESULTS_DIR,
        languages=["en"],
        gpu=False,
        paragraph=True,
        use_sorted_reading_order=False,
    )
    print(f"  Done   ({easyocr_count} images)\n")

    print("[2/6] Tesseract Inference")
    tesseract_count = run_tesseract_folder(
        input_dir=RENDERS_DIR,
        output_dir=TESSERACT_RESULTS_DIR,
        tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        lang="eng",
        psm=6,
        oem=3,
        timeout=10.0,
    )
    print(f"  Done   ({tesseract_count} images)\n")

    print("[3/6] GOT-OCR2 Inference")
    gotocr_count = run_gotocr_folder(
        input_dir=RENDERS_DIR,
        output_dir=GOTOCR_RESULTS_DIR,
        model_name="stepfun-ai/GOT-OCR-2.0-hf",
        device=None,
        max_new_tokens=1024,
    )
    print(f"  Done   ({gotocr_count} images)\n")

    print("[4/6] EasyOCR Character Accuracy Evaluation")
    easyocr_scores = evaluate_ocr_folder_with_manifest(EASYOCR_RESULTS_DIR, manifest)
    print_engine_results(EASYOCR_RESULTS_DIR, easyocr_scores, "EasyOCR")

    print("[5/6] Tesseract Character Accuracy Evaluation")
    tesseract_scores = evaluate_ocr_folder_with_manifest(TESSERACT_RESULTS_DIR, manifest)
    print_engine_results(TESSERACT_RESULTS_DIR, tesseract_scores, "Tesseract")

    print("[6/6] GOT-OCR2 Character Accuracy Evaluation")
    gotocr_scores = evaluate_ocr_folder_with_manifest(GOTOCR_RESULTS_DIR, manifest)
    print_engine_results(GOTOCR_RESULTS_DIR, gotocr_scores, "GOT-OCR2")

    print("\nPipeline complete.\n")


if __name__ == "__main__":
    main()