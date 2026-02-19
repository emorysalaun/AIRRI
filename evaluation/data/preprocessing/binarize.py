from pathlib import Path
import cv2
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

RENDERS_DIR = DATA_DIR / "renders"
BINARIZED_DIR = DATA_DIR / "binarized"
BINARIZED_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------
# Binarize all images in renders/
# -----------------------------------------

for image_path in sorted(RENDERS_DIR.iterdir()):
    if image_path.suffix.lower() not in [".png", ".jpg", ".jpeg"]:
        continue

    print("=" * 50)
    print("Processing:", image_path.name)

    # 1) Load image
    img = cv2.imread(str(image_path))

    # 2) grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    #Otsu Method
    _, binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # 4) Save
    output_path = BINARIZED_DIR / image_path.name
    cv2.imwrite(str(output_path), binary)

    print("Saved ->", output_path)

print("\nDone.")
