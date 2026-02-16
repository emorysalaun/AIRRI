from pathlib import Path
import easyocr
import warnings

warnings.filterwarnings("ignore")


BASE_DIR = Path(__file__).resolve().parent.parent
# Relative pathing
RENDERS_DIR = BASE_DIR / "data" / "renders"
RESULTS_DIR = BASE_DIR / "results" / "easyOCR"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

reader = easyocr.Reader(['en'], gpu=False)

for image_path in sorted(RENDERS_DIR.iterdir()):
    if image_path.suffix.lower() not in [".png", ".jpg", ".jpeg"]:
        continue

    print("=" * 50)
    print("FILE:", image_path.name)
    print("=" * 50)

    result = reader.readtext(str(image_path))
    texts = [txt for _, txt, _ in result]
    ocr_joined = " ".join(texts)

    print(ocr_joined)
    print()

    output_file = RESULTS_DIR / f"{image_path.stem}.txt"
    output_file.write_text(ocr_joined, encoding="utf-8")