from pathlib import Path
import easyocr
import warnings
from score import evaluate_ocr_folder

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RENDERS_DIR = DATA_DIR / "renders"
RESULTS_DIR = BASE_DIR / "results" / "easyocr"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def sort_reading_order(results, line_threshold=25):
    # Convert OCR output to centers
    boxes = []
    for bbox, text, conf in results:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]

        cx = sum(xs) / 4
        cy = sum(ys) / 4

        boxes.append({"x": cx, "y": cy, "text": text})

    # Cluster into lines by y (order independent)
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

    # Sort lines top-to-bottom
    lines.sort(key=lambda line: sum(b["y"] for b in line) / len(line))

    # Sort within each line left-to-right
    ordered_text = []
    for line in lines:
        line.sort(key=lambda b: b["x"])
        ordered_text.extend([b["text"] for b in line])

    return ordered_text

# ---------------------------------------------------
# Step — EasyOCR (runs directly on renders/)
# ---------------------------------------------------

print("\n=== AIRRI Evaluation Pipeline ===\n")
print("[1/2] EasyOCR Inference")

reader = easyocr.Reader(["en"], gpu=False)

render_images = sorted([
    p for p in RENDERS_DIR.iterdir()
    if p.suffix.lower() in [".png", ".jpg", ".jpeg"]
])

for image_path in render_images:
    print(f"  • {image_path.name}")

    result = reader.readtext(str(image_path), paragraph=True)
    texts = [r[1] for r in result]
    ocr_joined = " ".join(texts)

    output_file = RESULTS_DIR / f"{image_path.stem}.txt"
    output_file.write_text(ocr_joined, encoding="utf-8")

print(f"  Done ✓  ({len(render_images)} images)\n")



GROUND_TRUTH = """Home at Mount Vernon the candles in the windows of George Washington's home at Mount Vernon shone brightly on Christmas Eve. This Christmas Eve, though, was different. One month earlier the United States and Great Britain had signed a peace treaty ending the Revolutionary War. It was Christmastime when George Washington returned to his home. He was no longer the commander of the Continental Army. Soon after, at a dinner in New York, General Washington"""

print("[2/2] Character Accuracy Evaluation")

scores = evaluate_ocr_folder(RESULTS_DIR, GROUND_TRUTH)

for name, acc in scores.items():
    text = (RESULTS_DIR / name).read_text(encoding="utf-8")

    print(f"\n{name}")
    print("-" * 60)
    print(text)
    print(f"\nAccuracy → {acc:.2f}%\n")



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

print("\nPipeline complete ✓\n")
