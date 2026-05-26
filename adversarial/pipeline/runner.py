import sys
import time
import warnings
import json
import tempfile
import shutil
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime
import numpy as np
import torch
from PIL import Image

_ADV_DIR = str(Path(__file__).resolve().parents[1])
_EVAL_DIR = str(Path(__file__).resolve().parents[2] / "evaluation")
for _p in [_ADV_DIR, _EVAL_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from score import (
    evaluate_text_pair,
    evaluate_text_pair_wer,
)

from config import PipelineConfig
from utils.logger import ExperimentLogger
from engines import OCRModelWrapper, ENGINE_FNS
from attacks import get_attack
from renderer import TextRenderer
from region import match_semantic_to_visual, stitch_multi_region, stitch_adversarial, MatchedRegion
from llm import LLMLineSelector
from data import (
    load_manifest,
    filter_clean_manifest,
    pil_to_dataloader,
    save_composite_image,
)
from .dispatcher import dispatch_attack
from .reporter import PipelineReporter

warnings.filterwarnings("ignore")


class AdversarialPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = config.output_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = ExperimentLogger("adversarial_pipeline", str(self.log_dir))
        self.reporter = PipelineReporter(self.logger)

    def run(self):
        self.logger.section("AIRRI Adversarial Evaluation Pipeline")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Preload engines into VRAM to prevent lazy-loading bottleneck
        self.logger.info(f"Pre-loading engines into memory: {self.config.engines}")
        temp_in = Path(tempfile.mkdtemp())
        temp_out = Path(tempfile.mkdtemp())
        try:
            for engine_name in self.config.engines:
                if engine_name in ENGINE_FNS:
                    ENGINE_FNS[engine_name](temp_in, temp_out)
        finally:
            shutil.rmtree(temp_in, ignore_errors=True)
            shutil.rmtree(temp_out, ignore_errors=True)

        pipeline_start = time.perf_counter()

        # Iterate over each dataset subdirectory
        for ds in self.config.datasets:
            ds_name = ds["name"]
            manifest_path = self.config.dataset_root / ds["manifest"]

            self.logger.section(f"Dataset: {ds_name}")
            self.logger.info(f"  manifest : {manifest_path}")

            # Load manifest and filter to clean-only entries
            manifest = load_manifest(manifest_path)
            manifest = filter_clean_manifest(manifest)
            self.logger.info(f"  Loaded {len(manifest)} clean manifest entries")

            ds_output_dir = self.config.output_dir / ds_name

            # -- Step 1: LLM Line Selection caching for all manifest items up-front --
            self.logger.info("  Step 1: Running LLM line selection for all manifest items...")
            llm_selector = LLMLineSelector(
                model=self.config.llm_model,
                max_retries=self.config.llm_max_retries
            )
            manifest_selections = {}
            llm_cache_dir = ds_output_dir / "llm_selections"
            llm_cache_dir.mkdir(parents=True, exist_ok=True)

            for item in manifest:
                img_name = item["image_name"]
                base_name = Path(img_name).stem
                cache_path = llm_cache_dir / f"{base_name}.json"

                if cache_path.exists():
                    try:
                        with cache_path.open("r", encoding="utf-8") as f:
                            selected_lines = json.load(f)
                        self.logger.debug(f"    Loaded LLM selections for {img_name} from cache")
                    except Exception as e:
                        self.logger.warning(f"    Failed to load cache for {img_name}: {e}. Re-querying.")
                        selected_lines = llm_selector.select_important_lines(item["ground_truth"])
                        with cache_path.open("w", encoding="utf-8") as f:
                            json.dump(selected_lines, f, indent=2)
                else:
                    selected_lines = llm_selector.select_important_lines(item["ground_truth"])
                    with cache_path.open("w", encoding="utf-8") as f:
                        json.dump(selected_lines, f, indent=2)
                    self.logger.info(f"    Queried and cached LLM selections for {img_name}")

                manifest_selections[img_name] = selected_lines

            # -- Step 2: Render clean images for all ground-truth entries up-front --
            self.logger.info("  Step 2: Rendering clean images for all entries...")
            renderer = TextRenderer(
                font_path=self.config.render_font_path,
                font_size=self.config.render_font_size,
                wrap_width=self.config.render_wrap_width,
                margin_x=self.config.render_margin_x,
                margin_top=self.config.render_margin_top,
                margin_bottom=self.config.render_margin_bottom,
                line_padding=self.config.render_line_padding,
                bg_color=self.config.render_bg_color,
                text_color=self.config.render_text_color,
            )
            clean_renders_dir = ds_output_dir / "clean_renders"
            clean_renders_dir.mkdir(parents=True, exist_ok=True)
            rendered_images_map = {}

            for item in manifest:
                img_name = item["image_name"]
                rendered = renderer.render(item["ground_truth"], img_name)
                rendered.image.save(clean_renders_dir / img_name)
                rendered_images_map[img_name] = rendered

                # Crop and save standalone clean image crops for important declared lines
                important_lines = manifest_selections[img_name]
                matched_regions = match_semantic_to_visual(important_lines, rendered)
                if not matched_regions:
                    matched_regions = [
                        MatchedRegion(
                            semantic_line=vl.text,
                            visual_lines=[vl],
                            union_bbox=vl.bbox,
                            per_line_gt=vl.text,
                        )
                        for vl in rendered.lines
                    ]

                crops_dir = clean_renders_dir / "crops" / Path(img_name).stem
                crops_dir.mkdir(parents=True, exist_ok=True)
                for region in matched_regions:
                    for vl in region.visual_lines:
                        x1, y1, x2, y2 = vl.bbox
                        crop_img = rendered.image.crop((x1, y1, x2, y2))
                        crop_img.save(crops_dir / f"line_{vl.line_index:02d}.png")

            self.logger.info(f"  Rendered {len(manifest)} clean images and crop files to {clean_renders_dir}")

            # Run attack configurations
            self._run_dataset(manifest, rendered_images_map, manifest_selections, device, ds_output_dir)

        # Flush CSV safely at the end — combined across all datasets
        self.reporter.write_csv(self.config.output_dir / "all_scores.csv")

        total = time.perf_counter() - pipeline_start
        self.logger.section(f"Pipeline complete — {total:.2f}s total")

    def _run_dataset(self, manifest, rendered_images_map, manifest_selections, device, ds_output_dir):
        """Run all attack configs against the rendered images."""
        tasks = []
        for attack_name in self.config.attacks:
            eps_list = self.config.attack_eps.get(attack_name, [])
            for eps in eps_list:
                tasks.append((attack_name, eps))

        if not tasks:
            self.logger.warning("No attack tasks found. Skipping dataset.")
            return

        num_tasks = len(tasks)
        outer_workers = min(16, num_tasks)
        gpu_concurrency = 4

        self.logger.info(
            f"Dispatching {num_tasks} attack configs "
            f"(outer_workers={outer_workers}, "
            f"gpu_concurrency={gpu_concurrency})..."
        )

        gpu_semaphore = threading.Semaphore(gpu_concurrency)
        futures = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=outer_workers,
            thread_name_prefix="attack-config",
        ) as outer_executor:

            for attack_name, eps in tasks:
                future = outer_executor.submit(
                    self._run_attack_config,
                    attack_name,
                    eps,
                    rendered_images_map,
                    manifest_selections,
                    device,
                    gpu_semaphore,
                    manifest,
                    ds_output_dir,
                )
                futures.append(future)

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                    completed += 1
                    self.logger.info(
                        f"Completed {completed}/{num_tasks} attack configs"
                    )
                except Exception:
                    self.logger.exception("Outer config thread failed")

    def _run_attack_config(
        self,
        attack_name,
        eps,
        rendered_images_map,
        manifest_selections,
        device,
        gpu_semaphore,
        manifest,
        ds_output_dir,
    ):
        self.logger.section(f"Attack Config: {attack_name} @ eps={eps}")

        try:
            attack_fn = get_attack(attack_name)
        except ValueError as e:
            self.logger.error(str(e))
            return

        attack_dir = ds_output_dir / attack_name
        config_overrides = self.config.attack_configs.get(attack_name, {})
        eps_tag = f"eps_{eps:.4f}".rstrip("0").rstrip(".")

        engine_metrics = {
            eng: {"time": 0.0, "queries": 0}
            for eng in self.config.engines
            if eng in ENGINE_FNS
        }

        def _process_engine(engine_name, rendered_img, image_name, important_lines):
            start_time = time.perf_counter()

            matched_regions = match_semantic_to_visual(important_lines, rendered_img)
            if not matched_regions:
                # Fallback: attack all visual lines
                matched_regions = [
                    MatchedRegion(
                        semantic_line=vl.text,
                        visual_lines=[vl],
                        union_bbox=vl.bbox,
                        per_line_gt=vl.text,
                    )
                    for vl in rendered_img.lines
                ]

            clean_np = np.array(rendered_img.image.convert("RGB"), dtype=np.float32) / 255.0
            processed_line_indices = set()
            query_count = 0

            # Directories Setup
            composite_dir = attack_dir / eps_tag / engine_name / "composite_images"
            line_crops_dir = attack_dir / eps_tag / engine_name / "line_crops"
            results_full_dir = attack_dir / eps_tag / engine_name / "results_full"
            results_target_dir = attack_dir / eps_tag / engine_name / "results_target"

            composite_dir.mkdir(parents=True, exist_ok=True)
            line_crops_dir.mkdir(parents=True, exist_ok=True)
            results_full_dir.mkdir(parents=True, exist_ok=True)
            results_target_dir.mkdir(parents=True, exist_ok=True)

            def _ocr_pil_image(pil_img):
                t_in = Path(tempfile.mkdtemp())
                t_out = Path(tempfile.mkdtemp())
                try:
                    pil_img.save(t_in / "temp.png")
                    ENGINE_FNS[engine_name](t_in, t_out)
                    t_path = t_out / "temp.txt"
                    if t_path.exists():
                        return t_path.read_text(encoding="utf-8")
                    return ""
                finally:
                    shutil.rmtree(t_in, ignore_errors=True)
                    shutil.rmtree(t_out, ignore_errors=True)

            # Run Strategy B (per-line crop, attack, and process individually)
            perturbed_crops = []
            perturbed_bboxes = []
            perturbed_lines = []
            composite_name = f"{Path(image_name).stem}.png"

            for region in matched_regions:
                for vl in region.visual_lines:
                    if vl.line_index in processed_line_indices:
                        continue
                    processed_line_indices.add(vl.line_index)

                    # Load cropped line image from disk
                    crop_path = ds_output_dir / "clean_renders" / "crops" / Path(image_name).stem / f"line_{vl.line_index:02d}.png"
                    line_crop = Image.open(crop_path).convert("RGB")
                    line_loader = pil_to_dataloader(line_crop, batch_size=1)

                    ocr_model = OCRModelWrapper(engine_name, vl.text, self.config.cer_threshold)
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
                        perturbed_np = perturbed_batch[0].detach().cpu().permute(1, 2, 0).numpy()
                        perturbed_np = np.clip(perturbed_np, 0.0, 1.0)
                        query_count += ocr_model.query_count

                        # Save debug line crop
                        crop_arr = (perturbed_np * 255).astype(np.uint8)
                        line_crop_filename = f"{Path(image_name).stem}_line_{vl.line_index:02d}.png"
                        Image.fromarray(crop_arr).save(line_crops_dir / line_crop_filename)

                        # Evaluate Target Region OCR vs Per-Line Ground Truth for this perturbed line directly
                        perturbed_pil = Image.fromarray(crop_arr)
                        line_ocr_text = _ocr_pil_image(perturbed_pil)

                        with (results_target_dir / f"{Path(image_name).stem}_line_{vl.line_index:02d}.txt").open("w", encoding="utf-8") as f:
                            f.write(line_ocr_text)

                        line_cer = evaluate_text_pair(line_ocr_text, vl.text)
                        line_wer = evaluate_text_pair_wer(line_ocr_text, vl.text)

                        self.reporter.record_row(
                            image_name=composite_name,
                            engine_name=engine_name,
                            eps=eps,
                            attack_name=attack_name,
                            eval_scope="target_region",
                            target_line=vl.text,
                            cer=line_cer,
                            wer=line_wer
                        )

                        perturbed_crops.append(perturbed_np)
                        perturbed_bboxes.append(vl.bbox)
                        perturbed_lines.append(vl)

                    except Exception as e:
                        self.logger.warning(
                            f"      Attack on line {vl.line_index} failed: {e}. Keeping clean pixels."
                        )
                    finally:
                        ocr_model.cleanup()

            if perturbed_crops:
                try:
                    # Stitch all perturbed crops into clean background (Recreation phase)
                    composite_np = stitch_multi_region(clean_np, perturbed_crops, perturbed_bboxes)
                    
                    # Save the single composite image
                    save_composite_image(composite_np, composite_dir, composite_name)

                    # Evaluate 1: Full Composite OCR vs Full Ground Truth
                    composite_pil = Image.fromarray((composite_np * 255).astype(np.uint8))
                    full_ocr_text = _ocr_pil_image(composite_pil)

                    with (results_full_dir / f"{Path(image_name).stem}.txt").open("w", encoding="utf-8") as f:
                         f.write(full_ocr_text)

                    full_cer = evaluate_text_pair(full_ocr_text, rendered_img.full_text)
                    full_wer = evaluate_text_pair_wer(full_ocr_text, rendered_img.full_text)

                    self.reporter.record_row(
                        image_name=composite_name,
                        engine_name=engine_name,
                        eps=eps,
                        attack_name=attack_name,
                        eval_scope="full_composite",
                        target_line="all",
                        cer=full_cer,
                        wer=full_wer
                    )

                except Exception as e:
                    self.logger.error(
                        f"      Stitching or evaluation failed for {image_name}: {e}"
                    )

            elapsed = time.perf_counter() - start_time
            return engine_name, elapsed, query_count

        # Run process engines concurrently for each image
        for idx, item in enumerate(manifest, 1):
            image_name = item["image_name"]
            rendered_img = rendered_images_map[image_name]
            important_lines = manifest_selections[image_name]

            self.logger.info(
                f"  • Processing [{idx}/{len(manifest)}] {image_name} concurrently across {len(engine_metrics)} engines..."
            )

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(engine_metrics)
            ) as executor:
                futures = {
                    executor.submit(
                        _process_engine, eng, rendered_img, image_name, important_lines
                    ): eng
                    for eng in engine_metrics.keys()
                }

                for future in concurrent.futures.as_completed(futures):
                    try:
                        eng_name, elapsed, q_count = future.result()
                        engine_metrics[eng_name]["time"] += elapsed
                        engine_metrics[eng_name]["queries"] += q_count
                    except Exception as e:
                        self.logger.exception(f"Engine Thread Failed: {e}")

        for engine_name in engine_metrics.keys():
            self.logger.info(
                f"Engine '{engine_name}' metrics: time={engine_metrics[engine_name]['time']:.2f}s, queries={engine_metrics[engine_name]['queries']}"
            )
