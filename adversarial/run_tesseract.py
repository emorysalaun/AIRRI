import sys
from pathlib import Path

_ADV_DIR = str(Path(__file__).resolve().parent)
if _ADV_DIR not in sys.path:
    sys.path.insert(0, _ADV_DIR)

from config import PipelineConfig
from run_ocr import run_ocr_attacks

if __name__ == "__main__":
    config = PipelineConfig()
    try:
        run_ocr_attacks(config, "tesseract")
    except Exception as e:
        print(f"Error during Tesseract execution: {e}", file=sys.stderr)
        sys.exit(1)
