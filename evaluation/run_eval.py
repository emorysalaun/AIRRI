from pathlib import Path
import warnings

from engines.easyocr_engine import run_easyocr_folder
from engines.tesseract_engine import run_tesseract_folder
from engines.trocr_engine import run_trocr_folder

from score import evaluate_ocr_folder


warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

DATA_DIR = ROOT_DIR / "data"
RENDERS_DIR = DATA_DIR / "renders"

RESULTS_DIR = BASE_DIR / "results"

EASYOCR_RESULTS_DIR = RESULTS_DIR / "easyocr"
TESSERACT_RESULTS_DIR = RESULTS_DIR / "tesseract"
TROCR_RESULTS_DIR = RESULTS_DIR / "trocr"

GROUND_TRUTH = """Home at Mount Vernon the candles in the windows of George Washington's home at Mount Vernon shone brightly on Christmas Eve. This Christmas Eve, though, was different. One month earlier the United States and Great Britain had signed a peace treaty ending the Revolutionary War. It was Christmastime when George Washington returned to his home. He was no longer the commander of the Continental Army. Soon after, at a dinner in New York, General Washington"""


def print_engine_results(results_dir: Path, scores: dict[str, float], engine_name: str) -> None:
    print(f"\n--- {engine_name} Results ---")

    for name, acc in scores.items():
        text = (results_dir / name).read_text(encoding="utf-8")

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

    print("[3/6] TrOCR Inference")
    trocr_count = run_trocr_folder(
        input_dir=RENDERS_DIR,
        output_dir=TROCR_RESULTS_DIR,
        model_name="microsoft/trocr-small-printed",
        device=None,
        max_new_tokens=256,
    )
    print(f"  Done   ({trocr_count} images)\n")

    print("[4/6] EasyOCR Character Accuracy Evaluation")
    easyocr_scores = evaluate_ocr_folder(EASYOCR_RESULTS_DIR, GROUND_TRUTH)
    print_engine_results(EASYOCR_RESULTS_DIR, easyocr_scores, "EasyOCR")

    print("[5/6] Tesseract Character Accuracy Evaluation")
    tesseract_scores = evaluate_ocr_folder(TESSERACT_RESULTS_DIR, GROUND_TRUTH)
    print_engine_results(TESSERACT_RESULTS_DIR, tesseract_scores, "Tesseract")

    print("[6/6] TrOCR Character Accuracy Evaluation")
    trocr_scores = evaluate_ocr_folder(TROCR_RESULTS_DIR, GROUND_TRUTH)
    print_engine_results(TROCR_RESULTS_DIR, trocr_scores, "TrOCR")

    print("\nPipeline complete.\n")


if __name__ == "__main__":
    main()