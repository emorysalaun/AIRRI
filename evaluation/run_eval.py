from pathlib import Path
import json
import warnings
import csv

from engines.easyocr_engine import run_easyocr_folder
from engines.tesseract_engine import run_tesseract_folder
from engines.gotocr_engine import run_gotocr_folder

from score import evaluate_ocr_folder_with_manifest
from score import evaluate_ocr_folder_with_manifest_wer


warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RENDERS_DIR = DATA_DIR / "renders"
MANIFEST_PATH = DATA_DIR / "manifest.json"

RESULTS_DIR = BASE_DIR / "results"

EASYOCR_RESULTS_DIR = RESULTS_DIR / "easyocr"
TESSERACT_RESULTS_DIR = RESULTS_DIR / "tesseract"
GOTOCR_RESULTS_DIR = RESULTS_DIR / "gotocr"
CSV_PATH = RESULTS_DIR / "results.csv"

def append_result(image_name: str, model: str, accuracy: float):
    file_exists = CSV_PATH.exists()

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["image_name", "model", "accuracy"])

        writer.writerow([image_name, model, round(accuracy, 4)])


def load_manifest(manifest_path: Path) -> list[dict]:
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("manifest.json must contain a list of entries")

    for item in data:
        if "image_name" not in item or "ground_truth" not in item:
            raise ValueError("Each manifest entry must have 'image_name' and 'ground_truth'")

    return data


def print_engine_results(
    results_dir: Path,
    cer_scores: dict[str, float],
    wer_scores: dict[str, float],
    engine_name: str
) -> None:
    print(f"\n--- {engine_name} Results ---")

    for name in cer_scores:
        cer = cer_scores[name]
        wer = wer_scores.get(name, 0.0)

        text_path = results_dir / name
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else "[Missing OCR output file]"

        print(f"\n{name}")
        print("-" * 60)
        print(text)
        print(f"\nCER → {cer:.2f}%")
        print(f"WER → {wer:.2f}%\n")

        append_result(name, engine_name + "_CER", cer)
        append_result(name, engine_name + "_WER", wer)

    if not cer_scores:
        print("No results found.")
        return

    print("\nSummary")
    print("-" * 39)

    cer_values = list(cer_scores.values())
    wer_values = list(wer_scores.values())

    cer_avg = sum(cer_values) / len(cer_values)
    wer_avg = sum(wer_values) / len(wer_values)

    best_file = max(cer_scores, key=cer_scores.get)
    worst_file = min(cer_scores, key=cer_scores.get)

    print(f"Images evaluated : {len(cer_scores)}")
    print(f"Average CER      : {cer_avg:.2f}%")
    print(f"Average WER      : {wer_avg:.2f}%")
    print(f"Best CER result  : {best_file} ({cer_scores[best_file]:.2f}%)")
    print(f"Worst CER result : {worst_file} ({cer_scores[worst_file]:.2f}%)")


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

    # print("[3/6] GOT-OCR2 Inference")
    # gotocr_count = run_gotocr_folder(
    #     input_dir=RENDERS_DIR,
    #     output_dir=GOTOCR_RESULTS_DIR,
    #     model_name="stepfun-ai/GOT-OCR-2.0-hf",
    #     device=None,
    #     max_new_tokens=1024,
    # )
    # print(f"  Done   ({gotocr_count} images)\n")

    print("[4/6] EasyOCR Evaluation (CER + WER)")
    easyocr_cer = evaluate_ocr_folder_with_manifest(EASYOCR_RESULTS_DIR, manifest)
    easyocr_wer = evaluate_ocr_folder_with_manifest_wer(EASYOCR_RESULTS_DIR, manifest)
    print_engine_results(EASYOCR_RESULTS_DIR, easyocr_cer, easyocr_wer, "EasyOCR")

    print("[5/6] Tesseract Evaluation (CER + WER)")
    tesseract_cer = evaluate_ocr_folder_with_manifest(TESSERACT_RESULTS_DIR, manifest)
    tesseract_wer = evaluate_ocr_folder_with_manifest_wer(TESSERACT_RESULTS_DIR, manifest)
    print_engine_results(TESSERACT_RESULTS_DIR, tesseract_cer, tesseract_wer, "Tesseract")

    # print("[6/6] GOT-OCR2 Evaluation (CER + WER)")
    # gotocr_cer = evaluate_ocr_folder_with_manifest(GOTOCR_RESULTS_DIR, manifest)
    # gotocr_wer = evaluate_ocr_folder_with_manifest_wer(GOTOCR_RESULTS_DIR, manifest)
    # print_engine_results(GOTOCR_RESULTS_DIR, gotocr_cer, gotocr_wer, "GOT-OCR2")

    print("\nPipeline complete.\n")


if __name__ == "__main__":
    main()