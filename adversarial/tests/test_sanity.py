"""Sanity-check test — runs the full pipeline on 1 sample.

Generates a synthetic render from manifest entry #1, then runs
ALL attacks × ALL eps values × ALL engines with minimal query
budgets to verify the pipeline end-to-end.

Usage:
    python adversarial/tests/test_sanity.py
"""

import sys
import json
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Path setup ──────────────────────────────────────────────────────
_ADV_DIR = Path(__file__).resolve().parents[1]
_EVAL_DIR = _ADV_DIR.parent / "evaluation"
sys.path.insert(0, str(_ADV_DIR))
sys.path.insert(0, str(_EVAL_DIR))

RENDERS_DIR = _EVAL_DIR / "data" / "renders"
MANIFEST_PATH = _EVAL_DIR / "data" / "manifest.json"


# ── Step 1: Generate 1 synthetic render ─────────────────────────────

def generate_test_render():
    """Create a single text-on-white image from manifest entry #1."""
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    item = manifest[0]
    name = item["image_name"]
    text = item["ground_truth"][:300]  # enough text for OCR to read

    img = Image.new("RGB", (1024, 256), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16
        )
    except OSError:
        font = ImageFont.load_default()

    # wrap text into lines
    words = text.split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip()
        if font.getlength(test) < 1000:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)

    y = 10
    for line in lines:
        draw.text((10, y), line, fill="black", font=font)
        y += 22

    img.save(RENDERS_DIR / name)
    print(f"  Generated: {name} ({img.size[0]}x{img.size[1]})")
    return name


# ── Step 2: Run pipeline with minimal budgets ──────────────────────

def run_sanity_test():
    """Run ALL attacks × ALL eps × ALL engines on 1 image."""
    from config import PipelineConfig
    from pipeline import AdversarialPipeline

    # Minimal budgets for fast sanity check
    config = PipelineConfig(
        attacks=["smoo", "adba", "rays", "surfree"],
        attack_eps={
            "smoo": [10, 20],
            "adba": [4 / 255, 8 / 255, 16 / 255],
            "rays": [4 / 255, 8 / 255, 16 / 255],
            "surfree": [2, 3, 5],
        },
        engines=["easyocr", "tesseract", "gotocr", "trocr"],
        attack_configs={
            "smoo": {
                "iterations": 5,       # minimal iterations for test
                "pc": 0.85,
                "pm": 0.15,
                "pop_size": 2,         # minimal population
                "seed": 42,
            },
            "adba": {
                "budget": 10,          # minimal queries for test
                "init_dir": 1,
                "offspring_n": 2,
                "binary_mode": 0,
            },
            "rays": {
                "query_limit": 10,     # minimal queries for test
            },
            "surfree": {
                "init": {"steps": 5, "max_queries": 10},  # minimal
                "run": {},
            },
        },
    )

    print(f"\n  Config:")
    print(f"    attacks    : {config.attacks}")
    for atk in config.attacks:
        eps = config.attack_eps.get(atk, [])
        print(f"    {atk:10s} eps={eps}")
    print(f"    engines    : {config.engines}")
    print(f"    renders    : {config.renders_dir}")
    print(f"    output     : {config.output_dir}")

    start = time.time()
    pipeline = AdversarialPipeline(config)
    pipeline.run()
    elapsed = time.time() - start

    return config, elapsed


# ── Step 3: Verify output structure ────────────────────────────────

def verify_output(config, elapsed):
    """Check that all expected output files exist."""
    total_checks = 0
    passed = 0
    failed_items = []

    for attack in config.attacks:
        attack_dir = config.output_dir / attack
        csv_path = attack_dir / "scores.csv"

        # Check CSV exists
        total_checks += 1
        if csv_path.exists():
            passed += 1
            lines = csv_path.read_text().strip().split("\n")
            row_count = len(lines) - 1
        else:
            failed_items.append(f"{attack}/scores.csv MISSING")
            row_count = 0

        eps_list = config.attack_eps.get(attack, [])
        for eps in eps_list:
            eps_tag = f"eps_{eps:.4f}".rstrip("0").rstrip(".")
            for engine in config.engines:
                # Check perturbed images exist
                perturbed_dir = attack_dir / eps_tag / engine / "perturbed_images"
                total_checks += 1
                png_count = (
                    len(list(perturbed_dir.glob("*.png")))
                    if perturbed_dir.exists()
                    else 0
                )
                if png_count > 0:
                    passed += 1
                else:
                    failed_items.append(
                        f"{attack}/{eps_tag}/{engine}/perturbed_images: 0 PNGs"
                    )

                # Check OCR results exist
                results_dir = attack_dir / eps_tag / engine / "results"
                total_checks += 1
                txt_count = (
                    len(list(results_dir.glob("*.txt")))
                    if results_dir.exists()
                    else 0
                )
                if txt_count > 0:
                    passed += 1
                else:
                    failed_items.append(
                        f"{attack}/{eps_tag}/{engine}/results: 0 TXTs"
                    )

    # Check log files
    log_dir = config.output_dir / "logs"
    total_checks += 1
    log_files = list(log_dir.glob("*.log")) if log_dir.exists() else []
    if log_files:
        passed += 1
    else:
        failed_items.append("logs/*.log MISSING")

    # Print results
    print(f"\n{'=' * 60}")
    print("SANITY CHECK RESULTS")
    print(f"{'=' * 60}")
    print(f"  Elapsed   : {elapsed:.1f}s")
    print(f"  Checks    : {passed}/{total_checks} passed")

    if failed_items:
        print(f"\n  FAILURES ({len(failed_items)}):")
        for item in failed_items:
            print(f"Failed: {item}")
    else:
        print(f"\n  ALL CHECKS PASSED")

    print(f"{'=' * 60}")
    return passed == total_checks



if __name__ == "__main__":
    print("=" * 60)
    print("AIRRI Adversarial Pipeline — Sanity Check (1 sample)")
    print("=" * 60)

    print("\n[1/3] Generating synthetic test render...")
    generate_test_render()

    print("\n[2/3] Running full pipeline (minimal budgets)...")
    config, elapsed = run_sanity_test()

    print("\n[3/3] Verifying output structure...")
    ok = verify_output(config, elapsed)

    sys.exit(0 if ok else 1)
