"""AdversarialPipeline — orchestrates attack → OCR → score loop."""

import sys
import time
import warnings
from pathlib import Path
from datetime import datetime

import torch

# Ensure adversarial/ and evaluation/ are importable
_ADV_DIR = str(Path(__file__).resolve().parents[1])
_EVAL_DIR = str(Path(__file__).resolve().parents[2] / "evaluation")
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
    """End-to-end adversarial evaluation: perturb images, run OCR, score."""

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
        self.logger.info(f"Attacks    : {self.config.attacks}")
        self.logger.info(f"Attack eps : {self.config.attack_eps}")
        self.logger.info(f"Engines    : {self.config.engines}")
        self.logger.info(f"Renders    : {self.config.renders_dir}")
        self.logger.info(f"Output     : {self.config.output_dir}")

        renders = get_render_images(self.config.renders_dir)
        if not renders:
            self.logger.error("No render images found. Aborting.")
            return
        self.logger.info(f"Found {len(renders)} render images")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Device: {device}")

        pipeline_start = time.perf_counter()

        for attack_name in self.config.attacks:
            self._run_attack(attack_name, renders, device)

        total = time.perf_counter() - pipeline_start
        self.logger.section(f"Pipeline complete — {total:.2f}s total")

    def _run_attack(self, attack_name, renders, device):
        self.logger.section(f"Attack: {attack_name}")

        try:
            attack_fn = get_attack(attack_name)
        except ValueError as e:
            self.logger.error(str(e))
            return

        attack_dir = self.config.output_dir / attack_name
        config_overrides = self.config.attack_configs.get(attack_name, {})
        eps_list = self.config.attack_eps.get(attack_name, [])

        for eps_idx, eps in enumerate(eps_list, 1):
            self.logger.subsection(
                f"[{eps_idx}/{len(eps_list)}] {attack_name} @ eps={eps}"
            )

            eps_tag = f"eps_{eps:.4f}".rstrip("0").rstrip(".")

            for engine_name in self.config.engines:
                if engine_name not in ENGINE_FNS:
                    self.logger.warning(f"Unknown engine '{engine_name}', skipping")
                    continue

                self.logger.info(f"Engine: {engine_name}")
                perturbed_dir = attack_dir / eps_tag / engine_name / "perturbed_images"

                gt_map = {
                    item["image_name"]: item["ground_truth"] for item in self.manifest
                }
                total_queries = 0
                total_time = 0

                try:
                    for render_path in renders:
                        render_name = render_path.name
                        gt_text = gt_map.get(render_name, "")
                        if not gt_text:
                            self.logger.warning(f"No ground truth for {render_name}")
                            continue

                        ocr_model = OCRModelWrapper(
                            engine_name, gt_text, self.config.cer_threshold
                        )

                        try:
                            data_loader = images_to_dataloader(
                                [render_path], batch_size=1
                            )
                            start = time.perf_counter()

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
                            total_time += elapsed
                            total_queries += ocr_model.query_count

                            save_adversarial_images(
                                adv_loader, perturbed_dir, [render_name]
                            )
                        finally:
                            ocr_model.cleanup()

                    self.logger.info(
                        f"Attack complete in {total_time:.2f}s ({total_queries} OCR queries)"
                    )
                    self.logger.info(f"Saved perturbed images → {perturbed_dir}")

                    engine_results_dir = attack_dir / eps_tag / engine_name / "results"
                    engine_results_dir.mkdir(parents=True, exist_ok=True)

                    ENGINE_FNS[engine_name](perturbed_dir, engine_results_dir)

                    cer_scores = evaluate_ocr_folder_with_manifest(
                        engine_results_dir, self.manifest
                    )
                    wer_scores = evaluate_ocr_folder_with_manifest_wer(
                        engine_results_dir, self.manifest
                    )

                    self.reporter.record_scores(
                        engine_name, eps, cer_scores, wer_scores
                    )

                except Exception as e:
                    self.logger.exception(
                        f"Failed: {attack_name}/{engine_name}/eps={eps}: {e}"
                    )

        self.reporter.write_csv(attack_dir / "scores.csv")
