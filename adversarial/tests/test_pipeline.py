"""End-to-end test for the adversarial pipeline.

Generates 1 synthetic render image from the manifest, then runs
all attacks x all engines to verify everything works.

Usage:
    python adversarial/tests/test_pipeline.py
"""

import sys
import json
import textwrap
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
    """Create 1 text-on-white image and a dummy manifest for the test."""
    test_renders_dir = _ADV_DIR / "tests" / "test_renders"
    test_renders_dir.mkdir(parents=True, exist_ok=True)
    test_manifest_path = _ADV_DIR / "tests" / "test_manifest.json"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    item = manifest[0]
    name = item["image_name"]
    text = item["ground_truth"]

    # Wrap text and set image size to adapt to any size text
    lines = textwrap.wrap(text, width=80)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()

    # Calculate required image dimensions based on text length
    dummy_img = Image.new("RGB", (1, 1), color="white")
    draw_dummy = ImageDraw.Draw(dummy_img)

    max_w = 0
    total_h = 20
    for line in lines:
        bbox = draw_dummy.textbbox((0, 0), line, font=font)
        max_w = max(max_w, bbox[2] - bbox[0])
        total_h += (bbox[3] - bbox[1]) + 8  # line height + padding

    img_w = max_w + 40
    img_h = total_h + 20

    img = Image.new("RGB", (img_w, img_h), color="white")
    draw = ImageDraw.Draw(img)

    y_offset = 20
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text((20, y_offset), line, fill="black", font=font)
        y_offset += (bbox[3] - bbox[1]) + 8

    img.save(test_renders_dir / name)
    print(f"Generated test render: {name} (size: {img_w}x{img_h})")

    # Write a test manifest matching the full text
    with open(test_manifest_path, "w", encoding="utf-8") as f:
        json.dump([{"image_name": name, "ground_truth": text}], f, indent=2)

    return test_renders_dir, test_manifest_path


def run_pipeline_test(test_renders_dir, test_manifest_path):
    """Run the adversarial pipeline with all attacks x all engines."""
    from config import PipelineConfig
    from pipeline import AdversarialPipeline

    config = PipelineConfig(
        attacks=["adba", "rays", "surfree"],
        attack_eps={
            "adba": [16 / 255],
            "rays": [16 / 255],
            "surfree": [3],
        },
        engines=["easyocr", "tesseract", "gotocr", "trocr"],
        renders_dir=test_renders_dir,
        manifest_path=test_manifest_path,
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
            print(f"  {eps_tag}:")

            for engine in config.engines:
                engine_dir = attack_dir / eps_tag / engine
                perturbed_dir = engine_dir / "perturbed_images"
                results_dir = engine_dir / "results"

                img_count = (
                    len(list(perturbed_dir.glob("*.png")))
                    if perturbed_dir.exists()
                    else 0
                )
                txt_count = (
                    len(list(results_dir.glob("*.txt"))) if results_dir.exists() else 0
                )
                print(
                    f"    {engine}: {img_count} perturbed images, {txt_count} OCR result files"
                )

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
    test_renders_dir, test_manifest_path = generate_test_render()

    print("\n[2/2] Running adversarial pipeline...")
    run_pipeline_test(test_renders_dir, test_manifest_path)
