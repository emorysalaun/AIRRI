from pathlib import Path
import json
import warnings
import csv
import time

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

def print_overall_results(all_results: list[tuple[str, dict[str, float], dict[str, float]]]) -> None:
    print("\n=== OVERALL PIPELINE RESULTS ===")

    overall_clean_cer = []
    overall_dirty_cer = []

    overall_clean_wer = []
    overall_dirty_wer = []

    for engine_name, cer_scores, wer_scores in all_results:
        split = calculate_split_averages(cer_scores, wer_scores)

        overall_clean_cer.extend(split["clean_cer"])
        overall_dirty_cer.extend(split["dirty_cer"])

        overall_clean_wer.extend(split["clean_wer"])
        overall_dirty_wer.extend(split["dirty_wer"])

    print("\nCombined Results Across ALL Models")
    print("-" * 45)

    if overall_clean_cer:
        print(f"Overall Clean CER : {sum(overall_clean_cer) / len(overall_clean_cer):.2f}%")
        print(f"Overall Clean WER : {sum(overall_clean_wer) / len(overall_clean_wer):.2f}%")

    if overall_dirty_cer:
        print(f"Overall Dirty CER : {sum(overall_dirty_cer) / len(overall_dirty_cer):.2f}%")
        print(f"Overall Dirty WER : {sum(overall_dirty_wer) / len(overall_dirty_wer):.2f}%")

    print()

def print_engine_results(
    results_dir: Path,
    cer_scores: dict[str, float],
    wer_scores: dict[str, float],
    engine_name: str
) -> None:
    print(f"\n--- {engine_name} Results ---")

    split = calculate_split_averages(cer_scores, wer_scores)

    clean_cer_values = split["clean_cer"]
    dirty_cer_values = split["dirty_cer"]

    clean_wer_values = split["clean_wer"]
    dirty_wer_values = split["dirty_wer"]

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


    best_file = max(cer_scores, key=cer_scores.get)
    worst_file = min(cer_scores, key=cer_scores.get)

    print(f"Images evaluated : {len(cer_scores)}")


    if clean_cer_values:
        print(f"\nClean Average CER : {sum(clean_cer_values) / len(clean_cer_values):.2f}%")
        print(f"Clean Average WER : {sum(clean_wer_values) / len(clean_wer_values):.2f}%")

    if dirty_cer_values:
        print(f"Dirty Average CER : {sum(dirty_cer_values) / len(dirty_cer_values):.2f}%")
        print(f"Dirty Average WER : {sum(dirty_wer_values) / len(dirty_wer_values):.2f}%")

    print(f"\nBest CER result  : {best_file} ({cer_scores[best_file]:.2f}%)")
    print(f"Worst CER result : {worst_file} ({cer_scores[worst_file]:.2f}%)")

def calculate_split_averages(
    cer_scores: dict[str, float],
    wer_scores: dict[str, float],
):
    clean_cer = []
    dirty_cer = []

    clean_wer = []
    dirty_wer = []

    for name in cer_scores:
        cer = cer_scores[name]
        wer = wer_scores.get(name, 0.0)

        if "dirty" in name.lower():
            dirty_cer.append(cer)
            dirty_wer.append(wer)
        elif "clean" in name.lower():
            clean_cer.append(cer)
            clean_wer.append(wer)
        else:
            print("Filenames MUST include clean/dirty in the title. Neither detected.")

    return {
        "clean_cer": clean_cer,
        "dirty_cer": dirty_cer,
        "clean_wer": clean_wer,
        "dirty_wer": dirty_wer,
    }

def main() -> None:
    manifest = load_manifest(MANIFEST_PATH)

    pipeline_start = time.perf_counter()

    print("\n=== AIRRI Evaluation Pipeline ===\n")


    print("[1/6] EasyOCR Inference")

    start = time.perf_counter()

    easyocr_count = run_easyocr_folder(
        input_dir=RENDERS_DIR,
        output_dir=EASYOCR_RESULTS_DIR,
        languages=["en"],
        gpu=None,
        paragraph=True,
        use_sorted_reading_order=False,
    )

    elapsed = time.perf_counter() - start

    print(f"  Done   ({easyocr_count} images)")
    print(f"  Time   ({elapsed:.2f} seconds)\n")

    print("[2/6] Tesseract Inference")

    start = time.perf_counter()

    tesseract_count = run_tesseract_folder(
        input_dir=RENDERS_DIR,
        output_dir=TESSERACT_RESULTS_DIR,
        tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        lang="eng",
        psm=6,
        oem=3,
        timeout=10.0,
    )

    elapsed = time.perf_counter() - start

    print(f"  Done   ({tesseract_count} images)")
    print(f"  Time   ({elapsed:.2f} seconds)\n")

    print("[3/6] GOT-OCR2 Inference")

    start = time.perf_counter()

    gotocr_count = run_gotocr_folder(
        input_dir=RENDERS_DIR,
        output_dir=GOTOCR_RESULTS_DIR,
        model_name="stepfun-ai/GOT-OCR-2.0-hf",
        device=None,
        max_new_tokens=1024,
    )

    elapsed = time.perf_counter() - start

    print(f"  Done   ({gotocr_count} images)")
    print(f"  Time   ({elapsed:.2f} seconds)\n")

    print("[4/6] EasyOCR Evaluation (CER + WER)")

    start = time.perf_counter()

    easyocr_cer = evaluate_ocr_folder_with_manifest(
        EASYOCR_RESULTS_DIR,
        manifest
    )

    easyocr_wer = evaluate_ocr_folder_with_manifest_wer(
        EASYOCR_RESULTS_DIR,
        manifest
    )

    elapsed = time.perf_counter() - start

    print_engine_results(
        EASYOCR_RESULTS_DIR,
        easyocr_cer,
        easyocr_wer,
        "EasyOCR"
    )

    print(f"\n  Time   ({elapsed:.2f} seconds)\n")

    print("[5/6] Tesseract Evaluation (CER + WER)")

    start = time.perf_counter()

    tesseract_cer = evaluate_ocr_folder_with_manifest(
        TESSERACT_RESULTS_DIR,
        manifest
    )

    tesseract_wer = evaluate_ocr_folder_with_manifest_wer(
        TESSERACT_RESULTS_DIR,
        manifest
    )

    elapsed = time.perf_counter() - start

    print_engine_results(
        TESSERACT_RESULTS_DIR,
        tesseract_cer,
        tesseract_wer,
        "Tesseract"
    )

    print(f"\n  Time   ({elapsed:.2f} seconds)\n")

    print("[6/6] GOT-OCR2 Evaluation (CER + WER)")

    start = time.perf_counter()

    gotocr_cer = evaluate_ocr_folder_with_manifest(
        GOTOCR_RESULTS_DIR,
        manifest
    )

    gotocr_wer = evaluate_ocr_folder_with_manifest_wer(
        GOTOCR_RESULTS_DIR,
        manifest
    )

    elapsed = time.perf_counter() - start

    print_engine_results(
        GOTOCR_RESULTS_DIR,
        gotocr_cer,
        gotocr_wer,
        "GOT-OCR2"
    )

    print(f"\n  Time   ({elapsed:.2f} seconds)\n")

    all_results = [
        ("EasyOCR", easyocr_cer, easyocr_wer),
        ("Tesseract", tesseract_cer, tesseract_wer),
        ("GOT-OCR2", gotocr_cer, gotocr_wer),
    ]

    print_overall_results(all_results)

    total_elapsed = time.perf_counter() - pipeline_start

    print(f"\nTotal Pipeline Time: {total_elapsed:.2f} seconds")
    print("\nPipeline complete.\n")


if __name__ == "__main__":
    main()