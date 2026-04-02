from pathlib import Path
import warnings

from engines.easyocr_engine import run_easyocr_folder
from score import evaluate_ocr_folder


warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RENDERS_DIR = DATA_DIR / "renders"

RESULTS_DIR = BASE_DIR / "results"
EASYOCR_RESULTS_DIR = RESULTS_DIR / "easyocr"

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

    print("[1/2] EasyOCR Inference")
    image_count = run_easyocr_folder(
        input_dir=RENDERS_DIR,
        output_dir=EASYOCR_RESULTS_DIR,
        languages=["en"],
        gpu=False,
        paragraph=True,
        use_sorted_reading_order=False,
    )
    print(f"  Done   ({image_count} images)\n")

    print("[2/2] Character Accuracy Evaluation")
    scores = evaluate_ocr_folder(EASYOCR_RESULTS_DIR, GROUND_TRUTH)
    print_engine_results(EASYOCR_RESULTS_DIR, scores, "EasyOCR")

    print("\nPipeline complete.\n")


if __name__ == "__main__":
    main()