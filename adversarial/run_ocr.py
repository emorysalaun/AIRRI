"""Attack execution entry point — runs OCR attacks for a single engine."""

import concurrent.futures
import logging
import sys
import tempfile
import shutil
import threading
import time
from pathlib import Path
import numpy as np
import torch
from PIL import Image

_ADV_DIR = str(Path(__file__).resolve().parent)
_EVAL_DIR = str(Path(__file__).resolve().parent.parent / "evaluation")
for _p in [_ADV_DIR, _EVAL_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from score import (
    evaluate_text_pair,
    evaluate_text_pair_wer,
)

from config import PipelineConfig
from utils.logger import ExperimentLogger
from engines import OCRModelWrapper, ENGINE_FNS, run_ocr_on_pil
from attacks import get_attack
from region.stitcher import stitch_multi_region
from data.handler import load_dataset_manifest, pil_to_dataloader, save_composite_image
from pipeline.dispatcher import dispatch_attack
from pipeline.reporter import PipelineReporter

logger = logging.getLogger(__name__)


def _run_attack_config(
    config: PipelineConfig,
    engine_name: str,
    attack_name: str,
    eps: float,
    dataset_manifest: dict,
    device,
    gpu_semaphore: threading.Semaphore,
    log: ExperimentLogger,
    reporter: PipelineReporter,
):
    log.section(f"Attack Config: {attack_name} @ eps={eps}")

    attack_fn = get_attack(attack_name)
    config_overrides = config.attack_configs.get(attack_name, {})
    eps_tag = f"eps_{eps:.4f}".rstrip("0").rstrip(".")

    elapsed_time = 0.0
    query_count = 0

    for ds in dataset_manifest["datasets"]:
        ds_name = ds["name"]
        ds_output_dir = config.output_dir / ds_name
        attack_dir = ds_output_dir / attack_name

        for idx, item in enumerate(ds["items"], 1):
            image_name = item["image_name"]
            log.info(f"  • Processing [{idx}/{len(ds['items'])}] {image_name} on {engine_name}...")

            start_time = time.perf_counter()

            matched_regions = item["matched_regions"]
            if not matched_regions:
                raise ValueError(f"No matched regions found in manifest for {image_name}")

            clean_image_path = ds_output_dir / "clean_renders" / image_name
            clean_pil = Image.open(clean_image_path).convert("RGB")
            clean_np = np.array(clean_pil, dtype=np.float32) / 255.0

            processed_line_indices = set()

            composite_dir = attack_dir / eps_tag / engine_name / "composite_images"
            line_crops_dir = attack_dir / eps_tag / engine_name / "line_crops"
            results_full_dir = attack_dir / eps_tag / engine_name / "results_full"
            results_target_dir = attack_dir / eps_tag / engine_name / "results_target"

            composite_dir.mkdir(parents=True, exist_ok=True)
            line_crops_dir.mkdir(parents=True, exist_ok=True)
            results_full_dir.mkdir(parents=True, exist_ok=True)
            results_target_dir.mkdir(parents=True, exist_ok=True)

            perturbed_crops = []
            perturbed_bboxes = []
            composite_name = f"{Path(image_name).stem}.png"

            for region in matched_regions:
                for vl in region["visual_lines"]:
                    line_index = vl["line_index"]
                    line_text = vl["text"]
                    bbox = vl["bbox"]

                    if line_index in processed_line_indices:
                        continue
                    processed_line_indices.add(line_index)

                    crop_path = (
                        ds_output_dir
                        / "clean_renders"
                        / "crops"
                        / Path(image_name).stem
                        / f"line_{line_index:02d}.png"
                    )
                    line_crop = Image.open(crop_path).convert("RGB")
                    line_loader = pil_to_dataloader(line_crop, batch_size=1)

                    ocr_model = OCRModelWrapper(
                        engine_name, line_text, config.acc_threshold
                    )
                    try:
                        with gpu_semaphore:
                            adv_loader = dispatch_attack(
                                attack_name,
                                attack_fn,
                                ocr_model,
                                device,
                                line_loader,
                                eps,
                                config_overrides,
                            )

                        perturbed_batch = next(iter(adv_loader))[0]
                        perturbed_np = (
                            perturbed_batch[0].detach().cpu().permute(1, 2, 0).numpy()
                        )
                        perturbed_np = np.clip(perturbed_np, 0.0, 1.0)
                        query_count += ocr_model.query_count

                        crop_arr = (perturbed_np * 255).astype(np.uint8)
                        line_crop_filename = f"{Path(image_name).stem}_line_{line_index:02d}.png"
                        Image.fromarray(crop_arr).save(line_crops_dir / line_crop_filename)

                        perturbed_pil = Image.fromarray(crop_arr)
                        line_ocr_text = run_ocr_on_pil(perturbed_pil, engine_name)

                        with (
                            results_target_dir
                            / f"{Path(image_name).stem}_line_{line_index:02d}.txt"
                        ).open("w", encoding="utf-8") as f:
                            f.write(line_ocr_text)

                        line_acc = evaluate_text_pair(line_ocr_text, line_text)
                        line_word_acc = evaluate_text_pair_wer(line_ocr_text, line_text)

                        reporter.record_row(
                            image_name=composite_name,
                            engine_name=engine_name,
                            eps=eps,
                            attack_name=attack_name,
                            eval_scope="target_region",
                            target_line=line_text,
                            char_acc=line_acc,
                            word_acc=line_word_acc,
                        )

                        log.info(
                            f"      [Line {line_index}] finished. Queries: {ocr_model.query_count}, Accuracy: {line_acc:.2f}%"
                        )

                        perturbed_crops.append(perturbed_np)
                        perturbed_bboxes.append(bbox)

                    finally:
                        ocr_model.cleanup()

            if perturbed_crops:
                composite_np = stitch_multi_region(
                    clean_np, perturbed_crops, perturbed_bboxes
                )

                save_composite_image(composite_np, composite_dir, composite_name)

                composite_pil = Image.fromarray(
                    (composite_np * 255).astype(np.uint8)
                )
                full_ocr_text = run_ocr_on_pil(composite_pil, engine_name)

                with (results_full_dir / f"{Path(image_name).stem}.txt").open(
                    "w", encoding="utf-8"
                ) as f:
                    f.write(full_ocr_text)

                full_acc = evaluate_text_pair(full_ocr_text, item["full_text"])
                full_word_acc = evaluate_text_pair_wer(
                    full_ocr_text, item["full_text"]
                )

                reporter.record_row(
                    image_name=composite_name,
                    engine_name=engine_name,
                    eps=eps,
                    attack_name=attack_name,
                    eval_scope="full_composite",
                    target_line="all",
                    char_acc=full_acc,
                    word_acc=full_word_acc,
                )

            elapsed_time += time.perf_counter() - start_time

    log.info(f"Engine '{engine_name}' metrics: time={elapsed_time:.2f}s, queries={query_count}")


def run_ocr_attacks(config: PipelineConfig, engine_name: str):
    """Load prepared dataset, run all (attack, eps) combos for one engine.

    Raises if dataset_manifest.json not found or empty.
    """
    manifest_path = config.dataset_manifest_path
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Dataset manifest not found at {manifest_path}. "
            "Please run dataset_creation.py first."
        )

    dataset_manifest = load_dataset_manifest(manifest_path)
    if not dataset_manifest.get("datasets"):
        raise ValueError(f"Dataset manifest at {manifest_path} is empty.")

    log_dir = config.output_dir / "logs"
    log = ExperimentLogger(f"run_ocr_{engine_name}", str(log_dir))
    log.section(f"AIRRI Attack Stage for Engine: {engine_name}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Preload engine into VRAM
    log.info(f"Pre-loading engine into memory: {engine_name}")
    temp_in = Path(tempfile.mkdtemp())
    temp_out = Path(tempfile.mkdtemp())
    try:
        if engine_name in ENGINE_FNS:
            ENGINE_FNS[engine_name](temp_in, temp_out)
    finally:
        shutil.rmtree(temp_in, ignore_errors=True)
        shutil.rmtree(temp_out, ignore_errors=True)

    csv_path = config.output_dir / f"scores_{engine_name}.csv"
    reporter = PipelineReporter(csv_path)

    tasks = []
    for attack_name in config.attacks:
        eps_list = config.attack_eps.get(attack_name, [])
        for eps in eps_list:
            tasks.append((attack_name, eps))

    if not tasks:
        log.warning("No attack tasks found. Exiting.")
        return

    gpu_semaphore = threading.Semaphore(4)
    futures = []

    # Expensive VLM-based engines should not be parallelized — they share a
    # single GPU model and CUDA serializes the calls anyway, so extra threads
    # only add overhead and memory pressure.
    SERIAL_ENGINES = {"gotocr", "trocr"}
    n_workers = 1 if engine_name in SERIAL_ENGINES else min(16, len(tasks))

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=n_workers,
        thread_name_prefix="attack-config",
    ) as executor:
        for attack_name, eps in tasks:
            future = executor.submit(
                _run_attack_config,
                config,
                engine_name,
                attack_name,
                eps,
                dataset_manifest,
                device,
                gpu_semaphore,
                log,
                reporter,
            )
            futures.append(future)

        completed = 0
        for future in concurrent.futures.as_completed(futures):
            future.result()  # Propagate exceptions
            completed += 1
            log.info(f"Completed {completed}/{len(tasks)} attack configs")

    log.section(f"Attack Stage complete for Engine: {engine_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_ocr.py <engine_name>", file=sys.stderr)
        sys.exit(1)

    engine = sys.argv[1]
    config = PipelineConfig()
    try:
        run_ocr_attacks(config, engine)
    except Exception as e:
        print(f"Error running OCR attacks for {engine}: {e}", file=sys.stderr)
        sys.exit(1)
