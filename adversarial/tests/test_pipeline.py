"""End-to-end test for the adversarial pipeline.

Generates 1 synthetic render image from the manifest, then runs
all attacks x all engines to verify everything works.

Usage:
    python adversarial/tests/test_pipeline.py
"""

import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Path setup
_ADV_DIR = Path(__file__).resolve().parents[1]
_EVAL_DIR = _ADV_DIR.parent / "evaluation"
sys.path.insert(0, str(_ADV_DIR))
sys.path.insert(0, str(_EVAL_DIR))

RENDERS_DIR = _EVAL_DIR / "data" / "renders"
MANIFEST_PATH = _EVAL_DIR / "data" / "manifest.json"


def generate_test_render():
    """Create 1 text-on-white image from the first manifest entry."""
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    item = manifest[0]
    name = item["image_name"]
    text = item["ground_truth"][:200]

    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    draw.text((10, 10), text, fill="black", font=font)
    img.save(RENDERS_DIR / name)
    print(f"Generated test render: {name}")
    return 1


def run_pipeline_test():
    """Run the adversarial pipeline with all attacks x all engines."""
    from config import PipelineConfig
    from pipeline import AdversarialPipeline

    config = PipelineConfig(
        attacks=["smoo", "adba", "rays", "surfree"],
        attack_eps={
            "smoo": [10],
            "adba": [8 / 255],
            "rays": [8 / 255],
            "surfree": [3],
        },
        engines=["easyocr", "tesseract", "gotocr", "trocr"],
    )

    print(f"\nPipeline config:")
    print(f"  attacks    : {config.attacks}")
    print(f"  attack_eps : {config.attack_eps}")
    print(f"  engines    : {config.engines}")
    print(f"  renders    : {config.renders_dir}")
    print(f"  output     : {config.output_dir}")

    pipeline = AdversarialPipeline(config)
    pipeline.run()

    # verify output structure
    print(f"\n{'=' * 60}")
    print("VERIFICATION")
    print(f"{'=' * 60}")

    for attack in config.attacks:
        attack_dir = config.output_dir / attack
        csv_path = attack_dir / "scores.csv"
        print(f"\n{attack}/")
        print(f"  CSV exists: {csv_path.exists()}")

        if csv_path.exists():
            lines = csv_path.read_text().strip().split("\n")
            print(f"  CSV rows  : {len(lines) - 1} (excluding header)")

        eps_list = config.attack_eps.get(attack, [0.05])
        for eps in eps_list:
            eps_tag = f"eps_{eps:.4f}".rstrip("0").rstrip(".")
            perturbed_dir = attack_dir / eps_tag / "perturbed_images"
            count = len(list(perturbed_dir.glob("*.png"))) if perturbed_dir.exists() else 0
            print(f"  {eps_tag}: {count} perturbed images")

            for engine in config.engines:
                engine_dir = attack_dir / eps_tag / engine
                txt_count = len(list(engine_dir.glob("*.txt"))) if engine_dir.exists() else 0
                print(f"    {engine}: {txt_count} OCR result files")

    # check logs
    log_dir = config.output_dir / "logs"
    log_files = list(log_dir.glob("*.log")) if log_dir.exists() else []
    print(f"\nLog files: {len(log_files)}")
    if log_files:
        print(f"  → {log_files[-1].name}")

    print(f"\n{'=' * 60}")
    print("TEST COMPLETE")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    print("=" * 60)
    print("AIRRI Adversarial Pipeline — End-to-End Test")
    print("=" * 60)

    print("\n[1/2] Generating synthetic test render...")
    generate_test_render()

    print("\n[2/2] Running adversarial pipeline...")
    run_pipeline_test()
