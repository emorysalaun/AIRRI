import os
import easyocr
import warnings
warnings.filterwarnings("ignore")


RENDERS_DIR = "data/renders"

# Initialize reader
reader = easyocr.Reader(['en'], gpu=False)

# Only get pictures here.
for filename in sorted(os.listdir(RENDERS_DIR)):
    if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
        continue

    image_path = os.path.join(RENDERS_DIR, filename)

    print("=" * 60)
    print("FILE:", filename)
    print("=" * 60)

    result = reader.readtext(image_path)

    texts = [txt for _, txt, _ in result]
    ocr_joined = " ".join(texts)

    print(ocr_joined)
    print("\n")
