import sys
import time
import warnings
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
import torch
import threading
import concurrent.futures

_ADV_DIR = str(Path(__file__).resolve().parents[2])
_EVAL_DIR = str(Path(__file__).resolve().parents[3] / "evaluation")
for _p in [_ADV_DIR, _EVAL_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from score import (
    evaluate_ocr_folder_with_manifest,
    evaluate_ocr_folder_with_manifest_wer,
)

from config import PipelineConfig
from utils.logger import ExperimentLogger
from engines import OCRModelWrapper, ENGINE_FNS
from attacks import get_attack
from data import (
    load_manifest,
    filter_clean_manifest,
    get_render_images,
    images_to_dataloader,
    save_adversarial_images,
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
            renders_dir = self.config.dataset_root / ds["renders"]

            self.logger.section(f"Dataset: {ds_name}")
            self.logger.info(f"  manifest : {manifest_path}")
            self.logger.info(f"  renders  : {renders_dir}")

            # Load manifest and filter to clean-only entries
            manifest = load_manifest(manifest_path)
            manifest = filter_clean_manifest(manifest)
            self.logger.info(f"  Loaded {len(manifest)} clean manifest entries")

            renders = get_render_images(renders_dir)
            if not renders:
                self.logger.warning(
                    f"No render images found in {renders_dir}. Skipping dataset."
                )
                continue

            self.logger.info(f"  Found {len(renders)} render images")

            # Per-dataset output: output/UCONN/..., output/8and12_12/...
            ds_output_dir = self.config.output_dir / ds_name
            self._run_dataset(manifest, renders, device, ds_output_dir)

        # Flush CSV safely at the end — combined across all datasets
        self.reporter.write_csv(self.config.output_dir / "all_scores.csv")

        total = time.perf_counter() - pipeline_start
        self.logger.section(f"Pipeline complete — {total:.2f}s total")

    def _run_dataset(self, manifest, renders, device, ds_output_dir):
        """Run all attack configs against a single dataset's renders.

        Multi-threading architecture:
        - Outer ThreadPoolExecutor dispatches attack configs
        - GPU semaphore limits concurrent CUDA-heavy sections
        - Inner ThreadPoolExecutor (inside _run_attack_config)
          can run OCR engines concurrently
        """

        # Generate flat config task list
        tasks = []
        for attack_name in self.config.attacks:
            eps_list = self.config.attack_eps.get(attack_name, [])
            for eps in eps_list:
                tasks.append((attack_name, eps))

        if not tasks:
            self.logger.warning("No attack tasks found. Skipping dataset.")
            return

        num_tasks = len(tasks)

        # CPU-side concurrency
        outer_workers = min(16, num_tasks)

        # IMPORTANT:
        # Limit simultaneous GPU-heavy workloads.
        # Start conservatively and benchmark upward if needed.
        gpu_concurrency = 4

        self.logger.info(
            f"Dispatching {num_tasks} attack configs "
            f"(outer_workers={outer_workers}, "
            f"gpu_concurrency={gpu_concurrency})..."
        )

        # Shared semaphore for CUDA-heavy sections
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
                    renders,
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
        self, attack_name, eps, renders, device, gpu_semaphore, manifest, ds_output_dir
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
        gt_map = {item["image_name"]: item["ground_truth"] for item in manifest}

        engine_metrics = {
            eng: {"time": 0.0, "queries": 0}
            for eng in self.config.engines
            if eng in ENGINE_FNS
        }

        def _process_engine(engine_name, render_path, render_name, gt_text):
            ocr_model = OCRModelWrapper(engine_name, gt_text, self.config.cer_threshold)
            perturbed_dir = attack_dir / eps_tag / engine_name / "perturbed_images"
            perturbed_dir.mkdir(parents=True, exist_ok=True)
            try:
                data_loader = images_to_dataloader([render_path], batch_size=1)
                start = time.perf_counter()

                # Protect generation step using the safety ticket system
                with gpu_semaphore:
                    adv_loader = dispatch_attack(
                        attack_name,
                        attack_fn,
                        ocr_model,
                        device,
                        data_loader,
                        eps,
                        config_overrides,
                    )

                elapsed = time.perf_counter() - start
                save_adversarial_images(adv_loader, perturbed_dir, [render_name])
                return engine_name, elapsed, ocr_model.query_count
            finally:
                ocr_model.cleanup()

        for render_idx, render_path in enumerate(renders, 1):
            render_name = render_path.name
            gt_text = gt_map.get(render_name, "")
            if not gt_text:
                continue

            self.logger.info(
                f"  • Attacking [{render_idx}/{len(renders)}] {render_name} concurrently across {len(engine_metrics)} engines..."
            )
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(engine_metrics)
            ) as executor:
                futures = {
                    executor.submit(
                        _process_engine, eng, render_path, render_name, gt_text
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
                f"Engine '{engine_name}' attack complete in {engine_metrics[engine_name]['time']:.2f}s"
            )
            try:
                perturbed_dir = attack_dir / eps_tag / engine_name / "perturbed_images"
                engine_results_dir = attack_dir / eps_tag / engine_name / "results"
                engine_results_dir.mkdir(parents=True, exist_ok=True)
                ENGINE_FNS[engine_name](perturbed_dir, engine_results_dir)
                cer_scores = evaluate_ocr_folder_with_manifest(
                    engine_results_dir, manifest
                )
                wer_scores = evaluate_ocr_folder_with_manifest_wer(
                    engine_results_dir, manifest
                )
                self.reporter.record_scores(engine_name, eps, cer_scores, wer_scores)
            except Exception as e:
                self.logger.exception(
                    f"Failed scoring {attack_name}/{engine_name}/eps={eps}: {e}"
                )
