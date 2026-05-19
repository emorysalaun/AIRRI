"""Entry point for the AIRRI adversarial evaluation pipeline.

Usage:
    python adversarial/main.py
"""

import sys
from pathlib import Path

# Ensure adversarial/ and evaluation/ are importable
_ADV_DIR = Path(__file__).resolve().parent
_EVAL_DIR = _ADV_DIR.parent / "evaluation"
sys.path.insert(0, str(_ADV_DIR))
sys.path.insert(0, str(_EVAL_DIR))

from config import PipelineConfig
from pipeline import AdversarialPipeline

if __name__ == "__main__":
    config = PipelineConfig()
    pipeline = AdversarialPipeline(config)
    pipeline.run()
