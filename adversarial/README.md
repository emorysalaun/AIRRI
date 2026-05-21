# AIRRI — Adversarial Evaluation Pipeline

**Quick summary:** The pipeline loads dataset manifests and render images, generates adversarial images using a set of attack wrappers, runs OCR engines on perturbed images, computes OCR metrics (CER / WER), and writes per-image rows to CSVs. The entry point is [adversarial/main.py](adversarial/main.py#L1).

**Table of contents**

- **Overview**
- **Key modules & entry points**
- **Pipeline workflow (step-by-step)**
- **Configuration**
- **Data & manifest format**
- **Engines & evaluation**
- **Concurrency, GPU, and safety tickets**
- **Outputs & logs**
- **Running the pipeline and tests**
- **Known caveats / questions**

**Overview**

- The pipeline is implemented in `adversarial.pipeline.AdversarialPipeline` ([adversarial/pipeline/runner.py](adversarial/pipeline/runner.py#L1)).
- It orchestrates: dataset loading, attack dispatch, OCR running, scoring, and CSV reporting.

**Key modules & entry points**

- Entry point: [adversarial/main.py](adversarial/main.py#L1) — constructs `PipelineConfig()` and runs `AdversarialPipeline(config)`.
- Core pipeline: [adversarial/pipeline/runner.py](adversarial/pipeline/runner.py#L1).
- Attack registry: [adversarial/attacks/**init**.py](adversarial/attacks/__init__.py#L1) provides `get_attack(name)` which lazy-loads attack wrappers.
- Attack dispatch glue: [adversarial/pipeline/dispatcher.py](adversarial/pipeline/dispatcher.py#L1) — maps the unified call (attack_name, eps, overrides) to per-attack wrapper signatures.
- OCR engine wrapper: [adversarial/engines/ocr_wrapper.py](adversarial/engines/ocr_wrapper.py#L1) — wraps external OCR implementations as 2-class pseudo-classifiers for black-box attacks.
- Data handling: [adversarial/data/handler.py](adversarial/data/handler.py#L1) — manifest loader, render enumerator, dataloader conversion, and adversarial image saving.
- Result reporting: [adversarial/pipeline/reporter.py](adversarial/pipeline/reporter.py#L1) — buffers per-image rows and writes CSVs.

**Pipeline workflow (step-by-step)**

1. Preload & setup
   - `main.py` creates `PipelineConfig()` and `AdversarialPipeline(config)` then calls `pipeline.run()`.
   - Pipeline creates an `ExperimentLogger` and `PipelineReporter` for logging and CSV buffering ([adversarial/utils/logger.py](adversarial/utils/logger.py#L1)).
   - Engines are pre-loaded into temporary directories (see `ENGINE_FNS` in [adversarial/engines/ocr_wrapper.py](adversarial/engines/ocr_wrapper.py#L1)) to avoid lazy-loading bottlenecks (see `runner.py` pre-load loop near the top of `run()`).

2. Dataset loop
   - `PipelineConfig.datasets` controls which dataset subfolders to process. For each dataset entry the pipeline:
     - Loads manifest via `load_manifest(manifest_path)` ([adversarial/data/handler.py](adversarial/data/handler.py#L1)).
     - Filters to 'clean' images via `filter_clean_manifest()`.
     - Enumerates render images in the renders directory via `get_render_images()`.

3. Create attack tasks
   - The pipeline creates a flat list of (attack_name, eps) tasks using `config.attacks` and `config.attack_eps` (see `runner._run_dataset`).

4. Concurrency & dispatch
   - An outer `ThreadPoolExecutor` dispatches attack-config tasks concurrently (`max_workers = min(16, num_tasks)`).
   - A shared `threading.Semaphore` (default `gpu_concurrency = 4`) limits GPU-heavy sections where attacks or OCR engines may use CUDA.
   - For each (attack, eps), `_run_attack_config()` runs the attack across all render images.

5. Per-render, per-engine processing
   - For each render image the pipeline spawns an inner `ThreadPoolExecutor` sized to the number of configured engines.
   - Each engine is wrapped by `OCRModelWrapper(engine_name, ground_truth, cer_threshold)` ([adversarial/engines/ocr_wrapper.py](adversarial/engines/ocr_wrapper.py#L1)).
   - The attack generation step (the creation of adversarial images) is executed while holding the `gpu_semaphore` to limit concurrent GPU-heavy attack work.
   - After adversarial images are generated (returned as a DataLoader / iterator), `save_adversarial_images()` writes perturbed images to disk in `attack_dir/eps_tag/engine/perturbed_images`.

6. Scoring & reporting
   - After saving perturbed images, the pipeline invokes the corresponding OCR engine on the perturbed images (via `ENGINE_FNS[...]`) to produce OCR outputs (text files in a results folder).
   - Scoring is performed with functions imported from the evaluation package (`evaluate_ocr_folder_with_manifest` and `evaluate_ocr_folder_with_manifest_wer` — used in `runner._run_attack_config`).
   - `PipelineReporter.record_scores()` buffers per-image metrics and logs averages; `write_csv()` writes `all_scores.csv` under the main output directory at the end of the pipeline run.

**Configuration**

- See [adversarial/config.py](adversarial/config.py#L1) for the `PipelineConfig` dataclass. Key fields (with defaults from code):
  - `attacks`: list of attack names to run. Default: `['smoo','adba','rays','surfree']`.
  - `attack_eps`: dict mapping attack name to list of epsilon values (see file for defaults and units).
  - `attack_configs`: per-attack configuration dict (iterations, budgets, query limits, PGD steps, etc.).
  - `engines`: list of OCR engine names (default: `['easyocr','tesseract','gotocr','trocr']`).
  - `cer_threshold`: numeric threshold used inside `OCRModelWrapper` to decide when an OCR reading counts as 'correct'.
  - `dataset_root`: base path for datasets (default points to repository `dataset/` directory).
  - `datasets`: list of dataset dictionaries with `name`, `manifest`, and `renders` (relative to `dataset_root`).
  - `output_dir`: base output directory (default `adversarial/output`).

Note: `PipelineConfig` is instantiated with defaults in `main.py`. To change behavior, edit `adversarial/config.py` or create a wrapper script that constructs a `PipelineConfig` instance with modified fields and passes it to `AdversarialPipeline`.

**Data & manifest format**

- A manifest is a JSON array of objects. Each object must contain at least the keys `image_name` and `ground_truth` or `load_manifest()` raises a `ValueError` ([adversarial/data/handler.py](adversarial/data/handler.py#L1)).
- The pipeline filters manifest entries for those whose `image_name` contains the substring `clean` (case-insensitive) before attacking ([adversarial/data/handler.py](adversarial/data/handler.py#L1)).
- Render images are discovered via `get_render_images()` which accepts common image extensions (png, jpg, jpeg, bmp, tif, tiff, webp).

**Engines & evaluation**

- The adversarial package uses the `OCRModelWrapper` to adapt OCR engines into a model-like callable that returns 2-class pseudo-logits. See [adversarial/engines/ocr_wrapper.py](adversarial/engines/ocr_wrapper.py#L1).
- Engine invocation functions are provided by the evaluation package and are exposed via `ENGINE_FNS` (easyocr, tesseract, gotocr, trocr). The pipeline preloads these functions to warm models into memory before running the main attacks (see `runner.run`).
- Final scoring uses functions from the evaluation package: `evaluate_ocr_folder_with_manifest` and `evaluate_ocr_folder_with_manifest_wer` (imported in `runner.py`). The evaluation package contains the heavy OCR and metrics implementations — see `evaluation/requirements.txt` for the real runtime dependencies.

**Concurrency, GPU, and safety tickets**

- The pipeline uses two nested concurrency levels:
  - Outer: `ThreadPoolExecutor` dispatches (attack, eps) configurations in parallel (CPU-side concurrency).
  - Inner: per-render `ThreadPoolExecutor` runs multiple engine-wrappers concurrently for the same render.
- To bound GPU usage, a `threading.Semaphore` (default `gpu_concurrency = 4`) gates the attack generation step. This prevents more than N GPU-heavy attack generation sections running at the same time.

**Outputs & logs**

- Output directory layout (root = `config.output_dir`, default `adversarial/output`):
  - `<dataset_name>/<attack_name>/eps_<eps>/<engine>/perturbed_images/` — generated adversarial PNG images.
  - `<dataset_name>/<attack_name>/eps_<eps>/<engine>/results/` — OCR outputs (text files) after re-running engines on perturbed images.
  - `logs/` — pipeline logs created by `ExperimentLogger` ([adversarial/utils/logger.py](adversarial/utils/logger.py#L1)).
  - `all_scores.csv` — aggregate CSV written at the end of pipeline run by `PipelineReporter.write_csv()`.

**Running the pipeline**

1. Install Python dependencies required by the evaluation engines and the pipeline. The repository contains `evaluation/requirements.txt` which lists packages the evaluation engines require (including `torch`, `numpy`, `pillow`, `easyocr`, `pytesseract`, `transformers`, etc.). Install with:

```bash
python -m pip install -r evaluation/requirements.txt
```

2. Launch the pipeline (uses defaults from `adversarial/config.py`):

```bash
python adversarial/main.py
```

3. Run the end-to-end test (generates a synthetic render and runs selected attacks):

```bash
python adversarial/tests/test_pipeline.py
```

Notes about the test: `tests/test_pipeline.py` constructs a `PipelineConfig` instance with parameters `renders_dir` and `manifest_path` (see [adversarial/tests/test_pipeline.py](adversarial/tests/test_pipeline.py#L1)), but the `PipelineConfig` dataclass in [adversarial/config.py](adversarial/config.py#L1) does not define these fields. This may cause the test to fail unless the code has been adjusted elsewhere. Please confirm whether you want the test updated to use the `datasets`/`dataset_root` fields or whether additional compatibility layers exist.

**Known caveats & questions**

- Dependency scope: the pipeline relies on the evaluation package’s OCR engine implementations and scoring functions. For a complete environment, install `evaluation/requirements.txt`.
- Test / API mismatch: as noted above, `tests/test_pipeline.py` passes `renders_dir` and `manifest_path` to `PipelineConfig()` but those attributes are not present in `adversarial/config.py`. Do you want me to update the test or make `PipelineConfig` accept/handle these alternate constructor args?

If you'd like, I can:

- update `adversarial/config.py` to accept test-friendly constructor overrides, or
- update `adversarial/tests/test_pipeline.py` to construct a `PipelineConfig` consistent with the dataclass in `config.py`, or
- create a small CLI wrapper to pass runtime overrides without editing `config.py`.

---

Generated from repository source code. If you want the README to also include example outputs (sample CSV rows, sample log excerpt, or rendered directory tree), tell me which dataset/attack to run or I can run the test and attach the artifacts.
