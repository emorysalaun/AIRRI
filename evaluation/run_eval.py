from pathlib import Path
import cv2
import easyocr
import warnings

warnings.filterwarnings("ignore")

print("\n=== AIRRI Evaluation Pipeline ===\n")

# ---------------------------------------------------
# Directory setup (relative to evaluation/)
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RENDERS_DIR = DATA_DIR / "renders"
BINARIZED_DIR = DATA_DIR / "binarized"
RESULTS_DIR = BASE_DIR / "results" / "easyocr"

BINARIZED_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------
# Helper: sort OCR results in reading order
# ---------------------------------------------------

def sort_reading_order(results, line_threshold=25):
    # -------------------------------------------------
    # Convert OCR output to centers
    # -------------------------------------------------
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
            # compare with average y of existing line
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


# ---------------------------------------------------
# Step 1 — Binarization
# ---------------------------------------------------

print("Step 1: Binarizing images...\n")

image_paths = sorted([
    p for p in RENDERS_DIR.iterdir()
    if p.suffix.lower() in [".png", ".jpg", ".jpeg"]
])

for image_path in image_paths:
    print("Binarizing:", image_path.name)

    img = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    out_path = BINARIZED_DIR / image_path.name
    cv2.imwrite(str(out_path), binary)

print("\nBinarization complete.\n")

# ---------------------------------------------------
# Step 2 — EasyOCR
# ---------------------------------------------------

print("Step 2: Running EasyOCR...\n")

reader = easyocr.Reader(['en'], gpu=False)

binarized_images = sorted([
    p for p in BINARIZED_DIR.iterdir()
    if p.suffix.lower() in [".png", ".jpg", ".jpeg"]
])

for image_path in binarized_images:
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
