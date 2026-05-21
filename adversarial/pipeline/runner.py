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
        self.manifest = load_manifest(config.manifest_path)

    def run(self):
        self.logger.section("AIRRI Adversarial Evaluation Pipeline")
        renders = get_render_images(self.config.renders_dir)
        if not renders:
            self.logger.error("No render images found. Aborting.")
            return

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

        # Generate a flat list of config tasks
        tasks = []
        for attack_name in self.config.attacks:
            eps_list = self.config.attack_eps.get(attack_name, [])
            for eps in eps_list:
                tasks.append((attack_name, eps))

        self.logger.info(f"Dispatching {len(tasks)} parallel configs...")

        # ISSUE 16 TICKETS so 16 can be querying GPU simultaneously
        gpu_semaphore = threading.Semaphore(16)

        # Outer multithreading for Config execution
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(16, len(tasks))
        ) as outer_executor:
            futures = [
                outer_executor.submit(
                    self._run_attack_config,
                    attack_name,
                    eps,
                    renders,
                    device,
                    gpu_semaphore,
                )
                for (attack_name, eps) in tasks
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.exception(f"Outer Config Thread Failed: {e}")

        # Flush CSV safely at the end
        self.reporter.write_csv(self.config.output_dir / "all_scores.csv")

        total = time.perf_counter() - pipeline_start
        self.logger.section(f"Pipeline complete — {total:.2f}s total")

    def _run_attack_config(self, attack_name, eps, renders, device, gpu_semaphore):
        self.logger.section(f"Attack Config: {attack_name} @ eps={eps}")

        try:
            attack_fn = get_attack(attack_name)
        except ValueError as e:
            self.logger.error(str(e))
            return

        attack_dir = self.config.output_dir / attack_name
        config_overrides = self.config.attack_configs.get(attack_name, {})

        eps_tag = f"eps_{eps:.4f}".rstrip("0").rstrip(".")
        gt_map = {item["image_name"]: item["ground_truth"] for item in self.manifest}

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
                    engine_results_dir, self.manifest
                )
                wer_scores = evaluate_ocr_folder_with_manifest_wer(
                    engine_results_dir, self.manifest
                )
                self.reporter.record_scores(engine_name, eps, cer_scores, wer_scores)
            except Exception as e:
                self.logger.exception(
                    f"Failed scoring {attack_name}/{engine_name}/eps={eps}: {e}"
                )
