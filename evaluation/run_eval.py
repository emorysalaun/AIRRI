from pathlib import Path
import easyocr
import warnings

warnings.filterwarnings("ignore")

print("\n=== AIRRI Evaluation Pipeline (NO BINARIZATION) ===\n")


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

print("Step: Running EasyOCR on renders (no preprocessing)...\n")

reader = easyocr.Reader(["en"], gpu=False)

render_images = sorted([
    p for p in RENDERS_DIR.iterdir()
    if p.suffix.lower() in [".png", ".jpg", ".jpeg"]
])

for image_path in render_images:
    print("=" * 50)
    print("OCR FILE:", image_path.name)
    print("=" * 50)

    result = reader.readtext(str(image_path))
    texts = sort_reading_order(result)

    ocr_joined = " ".join(texts)

    print(ocr_joined)
    print()

    output_file = RESULTS_DIR / f"{image_path.stem}.txt"
    output_file.write_text(ocr_joined, encoding="utf-8")

print("\n=== Evaluation Complete ===\n")
