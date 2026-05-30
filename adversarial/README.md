# AIRRI Adversarial Pipeline — Technical Reference

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Pipeline Overview](#2-pipeline-overview)
3. [Module Map](#3-module-map)
4. [Step-by-Step Pipeline Walkthrough](#4-step-by-step-pipeline-walkthrough)
   - 4.1 [Manifest Loading and Filtering](#41-manifest-loading-and-filtering)
   - 4.2 [LLM Line Selection](#42-llm-line-selection)
   - 4.3 [Text Rendering](#43-text-rendering)
   - 4.4 [Semantic-to-Visual Matching](#44-semantic-to-visual-matching)
   - 4.5 [Line Cropping and Attack Execution](#45-line-cropping-and-attack-execution)
   - 4.6 [Stitching](#46-stitching)
   - 4.7 [Evaluation and Scoring](#47-evaluation-and-scoring)
5. [OCR Wrapper: Turning OCR into a Classifier](#5-ocr-wrapper-turning-ocr-into-a-classifier)
6. [Attack Registry and Dispatch](#6-attack-registry-and-dispatch)
7. [Concurrency Model](#7-concurrency-model)
8. [Scoring Functions](#8-scoring-functions)
9. [Configuration Reference](#9-configuration-reference)
10. [Output Directory Layout](#10-output-directory-layout)
11. [Execution Guide](#11-execution-guide)

---

## 1. Problem Statement

Standard adversarial attacks perturb every pixel of an image. This is wasteful for document images. A document has many lines of text, but only a few lines carry the actual assignment instructions. Perturbing the entire page wastes attack budget on irrelevant headers, due dates, and course logistics.

This pipeline takes a different approach: it asks an LLM to identify which lines in a document actually matter, crops just those lines out of the rendered image, runs adversarial attacks on the small crops, and pastes the perturbed crops back into the original clean image. The result is a document that looks nearly identical to the original but where the important lines have been subtly altered to fool OCR engines.

---

## 2. Pipeline Overview

The pipeline is split into two sequential stages:

1. **Dataset Creation Stage (`dataset_creation.py`):** Runs the LLM line selection, renders clean text-to-image outputs, crops/saves target region crops, and writes the `dataset_manifest.json` metadata catalog.
2. **Attack Execution Stage (`run_ocr.py`):** Loads the prepared `dataset_manifest.json` and executes attacks in parallel for a single specified OCR engine.

```mermaid
flowchart TB
    subgraph DC["Dataset Creation (dataset_creation.py)"]
        DC1["Load manifest.json"] --> DC2["Filter to clean entries"]
        DC2 --> DC3["Query LLM for important lines<br/>(cached to disk as JSON)"]
        DC2 --> DC4["Render ground truth text<br/>to clean PNG images"]
        DC4 --> DC5["Crop targeted visual lines<br/>and save as separate PNG crops"]
        DC3 --> DC5
        DC5 --> DC6["Save dataset_manifest.json"]
    end

    subgraph AE["Attack Execution (run_ocr.py)"]
        AE1["Load dataset_manifest.json"] --> AE2["Load each target line crop image from disk"]
        AE2 --> AE3["Wrap OCR engine as<br/>2-class pseudo-classifier"]
        AE3 --> AE4["Run black-box attack<br/>on the loaded crop image"]
        AE4 --> AE5["Collect perturbed crop images"]
        AE5 --> AE6["Stitch perturbed crop images<br/>back into original full clean image"]
        AE6 --> AE7["Run OCR on full composite image & target crops"]
        AE7 --> AE8["Compute CER & WER"]
        AE8 --> AE9["Write scores_<engine_name>.csv"]
    end

    DC -->|Produces manifest & crops| AE
```

---

## 3. Module Map

Each box below is a Python module in the `adversarial/` directory. Arrows show import dependencies.

```mermaid
flowchart LR
    dataset["dataset_creation.py"] --> config["config.py"]
    dataset --> llm["llm/line_selector.py"]
    dataset --> renderer["renderer/text_renderer.py"]
    dataset --> matcher["region/matcher.py"]
    dataset --> handler["data/handler.py"]

    run_ocr["run_ocr.py"] --> config
    run_ocr --> handler
    run_ocr --> wrapper["engines/ocr_wrapper.py"]
    run_ocr --> dispatcher["pipeline/dispatcher.py"]
    run_ocr --> stitcher["region/stitcher.py"]
    run_ocr --> reporter["pipeline/reporter.py"]
    run_ocr --> score["evaluation/score.py"]

    run_tess["run_tesseract.py"] --> run_ocr
    run_easy["run_easyocr.py"] --> run_ocr
    run_got["run_gotocr.py"] --> run_ocr
    run_tr["run_trocr.py"] --> run_ocr

    dispatcher --> attacks["attacks/__init__.py"]
    wrapper --> score
```

| Module              | File                        | Purpose                                                                                                                                         |
| :------------------ | :-------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| Dataset Entry point | `dataset_creation.py`       | Creates `PipelineConfig`, runs LLM selection, renders images, crops visual lines, saves `dataset_manifest.json`                                 |
| Attack Entry point  | `run_ocr.py`                | Load prepared `dataset_manifest.json` and runs all registered attack/epsilon configs for a single specified OCR engine                          |
| Engine Wrappers     | `run_*.py`                  | Thin wrapper scripts (`run_tesseract.py`, `run_easyocr.py`, `run_gotocr.py`, `run_trocr.py`) that call `run_ocr.py` with hardcoded engine names |
| Config              | `config.py`                 | Dataclass holding all pipeline settings (attacks, engines, epsilons, rendering parameters)                                                      |
| Dispatcher          | `pipeline/dispatcher.py`    | Maps each attack name to its specific function signature                                                                                        |
| Reporter            | `pipeline/reporter.py`      | Appends per-image score rows immediately to a thread-safe CSV file (`scores_<engine_name>.csv`)                                                 |
| LLM Selector        | `llm/line_selector.py`      | Runs local HuggingFace transformers inference to select important text excerpts                                                                 |
| Renderer            | `renderer/text_renderer.py` | Draws text onto images using PIL, records bounding boxes for each visual line                                                                   |
| Matcher             | `region/matcher.py`         | Maps LLM-selected text excerpts to visual line bounding boxes                                                                                   |
| Stitcher            | `region/stitcher.py`        | Pastes perturbed crops back into the clean image at their bounding boxes                                                                        |
| OCR Wrapper         | `engines/ocr_wrapper.py`    | Wraps OCR engines as 2-class classifiers for use with attack libraries, exports public `run_ocr_on_pil`                                         |
| Data Handler        | `data/handler.py`           | Loads manifests, converts images to DataLoaders, saves output images, reads/writes dataset manifests                                            |
| Scoring             | `evaluation/score.py`       | Computes character-level and word-level accuracy using Levenshtein distance                                                                     |
| Attack Registry     | `attacks/__init__.py`       | Registry for lazy-loading attack wrapper classes by name                                                                                        |

---

## 4. Step-by-Step Pipeline Walkthrough

### 4.1 Manifest Loading and Filtering

**Source**: `data/handler.py` — `load_manifest()` and `filter_clean_manifest()`

The dataset creation script reads a JSON manifest file. Each entry has two required fields:

```json
[
  {
    "image_name": "1_clean.png",
    "ground_truth": "The full text content of the document..."
  }
]
```

The function `filter_clean_manifest()` keeps only entries where `image_name` contains the substring `"clean"` (case-insensitive). This separates baseline images from any pre-existing adversarial variants in the dataset.

---

### 4.2 LLM Line Selection

**Source**: `llm/line_selector.py` — `LLMLineSelector.select_important_lines()`

For each manifest entry, the pipeline runs local LLM inference (default: `Qwen/Qwen3-32B` via HuggingFace `transformers`) to identify the verbatim lines that an LLM would need in order to complete the assignment. The model is loaded once into GPU memory (requires an A100 80GB or equivalent) and reused for all documents.

> **Note:** The first run will download the model weights (~64GB for BF16). Subsequent runs use the cached weights from the HuggingFace cache directory.

**What the prompt tells the LLM to select:**

- What the student is being asked to do
- What content, topic, problem, or question must be addressed
- What deliverables are required
- What constraints apply (format, length, citation style, etc.)
- What evaluation criteria define success

**What the prompt tells the LLM to ignore:**

- Course logistics, submission procedures, due dates
- Instructor contact information
- Generic academic integrity statements

The prompt explicitly states: _"The lines DO NOT need to be consecutive. They may come from completely different parts of the document."_

The LLM returns a JSON array of verbatim string excerpts (with Qwen3 thinking mode disabled for clean output). Each returned excerpt is validated:

1. **Exact match**: Check if the excerpt appears as a substring of the ground truth.
2. **Fuzzy match**: If exact match fails, normalize both strings by removing all whitespace, then try substring matching against the full text (handles multi-line spans). If a match is found, the original (non-normalized) text from the ground truth is used.
3. **No Fallback**: If inference fails after `max_retries` attempts, or if the response contains no valid excerpts, an exception is raised and the process aborts.

**Caching**: Selections are saved to disk as JSON files in `<output_dir>/<dataset>/llm_selections/<image_stem>.json`. On subsequent runs, cached results are loaded instead of re-running inference.

---

### 4.3 Text Rendering

**Source**: `renderer/text_renderer.py` — `TextRenderer.render()`

The pipeline renders the ground truth text into clean images from scratch. This gives the pipeline exact control over font, layout, and the precise pixel coordinates of every line.

**Rendering process:**

1. The text is word-wrapped using Python's `textwrap.wrap()` at a configurable column width (default: 90 characters).
2. A dummy 1×1 image is created to measure each wrapped line's pixel dimensions using `ImageDraw.textbbox()`.
3. The final image dimensions are computed:
   - Width = widest line + left margin + right margin
   - Height = top margin + sum of (line heights + padding between lines) + bottom margin
4. A white RGB image of those dimensions is created.
5. Each line is drawn at its computed position using `ImageDraw.text()`.
6. After drawing, `textbbox()` is called again at the actual draw position to get a tight bounding box.

The result is a `RenderedImage` object containing:

- The PIL image
- A list of `RenderedLine` objects, each with: the line text, its bounding box `(x1, y1, x2, y2)`, and its index (0-based)
- The full original text
- The image filename

---

### 4.4 Semantic-to-Visual Matching

**Source**: `region/matcher.py` — `match_semantic_to_visual()`

This function maps LLM-selected text excerpts to bounding boxes in the rendered image.

The matching works by character offsets in the full text:

**Step 1 — Build a character-offset map for each visual line:**

For each `RenderedLine`, find where its text starts and ends within `full_text`:

```
full_text: "Line one. Line two. Line three."
            ↑         ↑          ↑
            0         10         20

Visual line 0: chars  0..9   → bbox (15, 16, 200, 28)
Visual line 1: chars 10..19  → bbox (15, 33, 200, 45)
Visual line 2: chars 20..31  → bbox (15, 50, 200, 62)
```

The search is sequential: each line's start position is found by calling `full_text.find(line.text, previous_end)`.

**Step 2 — For each LLM excerpt, find overlapping visual lines:**

The excerpt's position in `full_text` is located (with a fuzzy fallback that normalizes whitespace). Two intervals overlap when:

```
max(line_start, excerpt_start) < min(line_end, excerpt_end)
```

All visual lines satisfying this condition are collected into a `MatchedRegion`.

**Step 3 — Compute the union bounding box:**

```
x1 = min of all matched lines' x1
y1 = min of all matched lines' y1
x2 = max of all matched lines' x2
y2 = max of all matched lines' y2
```

This handles excerpts that span multiple visual lines (because `textwrap` broke a long sentence across lines).

**No Fallback**: If matching produces zero regions for an image, an error is raised immediately.

---

### 4.5 Line Cropping and Attack Execution

**Source**: `run_ocr.py` — `_run_attack_config()`

For each image, the attack executor loads the prepared visual line crop images from the disk location:
`<ds_output_dir>/clean_renders/crops/<image_stem>/line_{line_index:02d}.png`

For each visual line:

1. **Convert to DataLoader**: The crop image is loaded and converted to a float32 tensor in `[0, 1]` range with shape `(1, 3, H, W)` and wrapped in a PyTorch `DataLoader` with a label of `1` (correctly read).
2. **Create OCR wrapper**: An `OCRModelWrapper` is created for this specific line, with the line's text as its ground truth.
3. **Run attack**: The attack function is called through `dispatch_attack()`, which handles the different argument conventions of each attack. The attack returns a `DataLoader` containing the perturbed image.
4. **Extract result**: The perturbed image is extracted from the returned DataLoader, converted back to a `(H, W, 3)` numpy array, and clipped to `[0, 1]`.

The attack execution is gated by a `gpu_semaphore` (see [Section 7](#7-concurrency-model)).

---

### 4.6 Stitching

**Source**: `region/stitcher.py` — `stitch_adversarial()` and `stitch_multi_region()`

After all target lines have been attacked, the perturbed crops are pasted back into the clean image background.

**The rule is simple**: for each perturbed crop and its bounding box, copy the crop's pixels into the corresponding region of the clean image. Everything outside the bounding boxes stays exactly as it was.

```
composite[y1:y2, x1:x2, :] = perturbed_crop
```

Coordinates are clamped to image bounds. The crop dimensions must match the bounding box dimensions exactly — if they don't, a `ValueError` is raised.

For multiple crops, `stitch_multi_region()` applies them sequentially.

The final composite is saved as a PNG to `<attack>/<eps>/<engine>/composite_images/`. Individual perturbed line crops are also saved separately to `line_crops/` for debugging.

---

### 4.7 Evaluation and Scoring

**Source**: `run_ocr.py` — inside `_run_attack_config()`, and `pipeline/reporter.py`

After stitching, the pipeline evaluates the composite image at two levels:

**Level 1 — Full composite evaluation:**

- OCR is run on the entire composite image using `run_ocr_on_pil()`.
- The extracted text is compared against the full ground truth text.
- CER and WER are computed and recorded with `eval_scope="full_composite"`.

**Level 2 — Per-line target evaluation:**

- For each attacked line, the pipeline crops that line's bounding box from the composite image.
- OCR is run on just that crop using `run_ocr_on_pil()`.
- The extracted text is compared against that specific line's ground truth text.
- CER and WER are computed and recorded with `eval_scope="target_region"`.

All score rows are recorded immediately to the CSV file `scores_<engine_name>.csv` in `<output_dir>/`.

---

## 5. OCR Wrapper: Turning OCR into a Classifier

**Source**: `engines/ocr_wrapper.py` — `OCRModelWrapper` and `run_ocr_on_pil()`

Adversarial attack libraries expect a model that takes an image tensor and returns class logits. OCR engines don't work that way — they take an image and return text. The `OCRModelWrapper` bridges this gap by turning OCR into a 2-class classification problem:

```
Class 0: "misread"  — OCR accuracy is below the threshold
Class 1: "correct"  — OCR accuracy is at or above the threshold
```

**How it works:**

When the attack calls `model(image_tensor)`:

1. The tensor (shape `(N, C, H, W)`, float `[0, 1]`) is converted to a PIL image.
2. The PIL image is evaluated using the public `run_ocr_on_pil(pil_img, engine_name, work_dir)` function.
3. The OCR output text is compared to the stored ground truth using `evaluate_text_pair()` to get an accuracy percentage.
4. If accuracy ≥ threshold → return `[[0.0, 1.0]]` (predict class 1: correct)
5. If accuracy < threshold → return `[[1.0, 0.0]]` (predict class 0: misread)

The attack's job is to flip the prediction from class 1 to class 0. Each call to `model(image_tensor)` counts as one query.

**Dynamic threshold adjustment**: On the first query (the clean image), if the OCR engine already reads the line poorly (accuracy below `cer_threshold`), the wrapper lowers its target. Specifically, it sets the threshold to the lesser of `(accuracy - 10)` and `(accuracy × 0.8)`, floored at 0. This prevents the attack from "succeeding" without actually doing anything.

**Disk I/O optimization**: Because attacks may issue hundreds of queries per line, the wrapper creates its temp directory on `/dev/shm` (Linux RAM disk) if available. This avoids SSD write bottlenecks during query-heavy attacks.

The supported OCR engines are loaded from `evaluation/engines/` using `importlib`:

| Engine key  | Function               | Source file                              |
| :---------- | :--------------------- | :--------------------------------------- |
| `easyocr`   | `run_easyocr_folder`   | `evaluation/engines/easyocr_engine.py`   |
| `tesseract` | `run_tesseract_folder` | `evaluation/engines/tesseract_engine.py` |
| `gotocr`    | `run_gotocr_folder`    | `evaluation/engines/gotocr_engine.py`    |
| `trocr`     | `run_trocr_folder`     | `evaluation/engines/trocr_engine.py`     |

---

## 6. Attack Registry and Dispatch

**Source**: `attacks/__init__.py` and `pipeline/dispatcher.py`

Attacks are registered in `ATTACK_REGISTRY`, a dictionary mapping string names to lazy-loading functions. The lazy loading means attack dependencies are only imported when that attack is actually used.

Each attack has a different calling convention. The `dispatch_attack()` function translates the pipeline's uniform `(attack_name, eps, config_overrides)` interface into the specific arguments each wrapper expects:

| Attack    | Epsilon meaning                                                                  | Key config fields                                  |
| :-------- | :------------------------------------------------------------------------------- | :------------------------------------------------- |
| `smoo`    | Pixel-level perturbation limit (converted to int if ≥ 1, else `int(eps × 1024)`) | `iterations`, `pc`, `pm`, `pop_size`, `seed`       |
| `adba`    | L∞ perturbation budget (passed as `epsilon`)                                     | `budget`, `init_dir`, `offspring_n`, `binary_mode` |
| `rays`    | L∞ perturbation budget (passed directly)                                         | `query_limit`                                      |
| `surfree` | L2 distance threshold (passed as `l2_threshold`)                                 | `init.steps`, `init.max_queries`                   |

---

## 7. Concurrency Model

**Source**: `run_ocr.py` — `run_ocr_attacks()`

The concurrency model runs attacks concurrently for different `(attack_name, epsilon)` configs for the single specified engine.

```mermaid
flowchart TB
    subgraph Outer["Outer ThreadPoolExecutor<br/>max_workers = min(16, num_tasks)"]
        T1["Task: adba @ eps=0.0157"]
        T2["Task: adba @ eps=0.0314"]
        T3["Task: rays @ eps=0.0627"]
    end

    subgraph GPU["GPU Semaphore (value=4)"]
        S["Limits concurrent<br/>attack generation"]
    end

    T1 -.->|acquire before attack| GPU
    T2 -.->|acquire before attack| GPU
    T3 -.->|acquire before attack| GPU

    style Outer fill:#d6eaf8,stroke:#2980b9,stroke-width:2px
    style GPU fill:#fadbd8,stroke:#e74c3c,stroke-width:2px
```

**Outer pool**: One thread per `(attack_name, epsilon)` combination. The pool is sized to `min(16, num_tasks)`.

**GPU semaphore**: A `threading.Semaphore` with a default value of 4. Each thread must acquire the semaphore before running `dispatch_attack()` and releases it afterward. This prevents more than 4 GPU-heavy operations from running simultaneously, avoiding CUDA out-of-memory errors.

---

## 8. Scoring Functions

**Source**: `evaluation/score.py`

### Character-Level Accuracy (CER-based)

`evaluate_text_pair(predicted, ground_truth)`:

1. Both strings are normalized: all whitespace is removed, and text is lowercased.
2. The Levenshtein edit distance between the normalized strings is computed.
3. Accuracy is calculated as:

```
accuracy = max(0, (1 - edit_distance / length_of_ground_truth)) × 100
```

### Word-Level Accuracy (WER-based)

`evaluate_text_pair_wer(predicted, ground_truth)`:

1. Both strings are tokenized into word lists by splitting on whitespace, then lowercased.
2. The Levenshtein distance is computed over the word lists (treating each word as a unit).
3. Accuracy is calculated as:

```
accuracy = max(0, (1 - edit_distance / number_of_ground_truth_words)) × 100
```

---

## 9. Configuration Reference

**Source**: `config.py` — `PipelineConfig`

| Field                  | Type          | Default                                       | Description                                                                     |
| :--------------------- | :------------ | :-------------------------------------------- | :------------------------------------------------------------------------------ |
| `attacks`              | `list[str]`   | `["smoo", "adba", "rays", "surfree"]`         | Which attacks to run                                                            |
| `attack_eps`           | `dict`        | See below                                     | Epsilon values per attack                                                       |
| `attack_configs`       | `dict`        | See below                                     | Hyperparameters per attack                                                      |
| `engines`              | `list[str]`   | `["easyocr", "tesseract", "gotocr", "trocr"]` | Which OCR engines to target                                                     |
| `cer_threshold`        | `float`       | `50.0`                                        | Accuracy boundary for the OCR wrapper's decision                                |
| `dataset_root`         | `Path`        | `<repo>/dataset/`                             | Base path for dataset directories                                               |
| `datasets`             | `list[dict]`  | UCONN + 8and12                                | Dataset entries with `name` and `manifest` path                                 |
| `output_dir`           | `Path`        | `adversarial/output/`                         | Where all output files are written                                              |
| `llm_model`            | `str`         | `"Qwen/Qwen3-32B"`                            | HuggingFace model ID for local LLM line selection (requires ~64GB VRAM in BF16) |
| `llm_max_retries`      | `int`         | `3`                                           | Max inference retries                                                           |
| `render_font_path`     | `str or None` | `None`                                        | Override font path                                                              |
| `render_font_size`     | `int`         | `12`                                          | Font size in points                                                             |
| `render_wrap_width`    | `int`         | `90`                                          | Character column width for word wrapping                                        |
| `render_margin_x`      | `int`         | `15`                                          | Left and right margin in pixels                                                 |
| `render_margin_top`    | `int`         | `16`                                          | Top margin in pixels                                                            |
| `render_margin_bottom` | `int`         | `17`                                          | Bottom margin in pixels                                                         |
| `render_line_padding`  | `int`         | `5`                                           | Vertical gap between lines in pixels                                            |
| `render_bg_color`      | `str`         | `"white"`                                     | Background color                                                                |
| `render_text_color`    | `str`         | `"black"`                                     | Text color                                                                      |

---

## 10. Output Directory Layout

```
adversarial/output/
├── dataset_manifest.json              ← complete prepared dataset catalog
│
├── <dataset_name>/
│   ├── clean_renders/
│   │   ├── <image_name>.png           ← rendered clean full-page image
│   │   └── crops/
│   │       └── <image_stem>/
│   │           └── line_00.png        ← standalone clean line crop image file
│   │
│   ├── llm_selections/
│   │   └── <image_stem>.json          ← cached LLM-selected excerpts
│   │
│   └── <attack_name>/
│       └── eps_<value>/
│           └── <engine_name>/
│               ├── composite_images/
│               │   └── <image_name>.png   ← full stitched result
│               │
│               ├── line_crops/
│               │   └── <stem>_line_00.png ← individual perturbed crops
│               │
│               ├── results_full/
│               │   └── <stem>.txt         ← OCR output on full composite
│               │
│               └── results_target/
│                   └── <stem>_line_00.txt  ← OCR output on target line crop
│
├── logs/
│   ├── dataset_creation.log
│   └── run_ocr_<engine_name>.log
│
└── scores_<engine_name>.csv            ← per-engine result scores
```

**CSV columns** (from `PipelineReporter`):

| Column        | Description                                                      |
| :------------ | :--------------------------------------------------------------- |
| `image_name`  | Source image filename                                            |
| `engine`      | OCR engine used                                                  |
| `eps`         | Perturbation budget                                              |
| `attack`      | Attack name                                                      |
| `eval_scope`  | `"full_composite"` or `"target_region"`                          |
| `target_line` | `"all"` for full composite, or the line's text for target region |
| `cer`         | Character-level accuracy (0–100, rounded to 4 decimal places)    |
| `wer`         | Word-level accuracy (0–100, rounded to 4 decimal places)         |

---

## 11. Execution Guide

### Prerequisites

- **GPU**: NVIDIA A100 80GB (or equivalent with ≥64GB VRAM)
- **Python environment**:
  ```bash
  module load conda/latest
  conda activate airri
  ```
- **Dependencies**:
  ```bash
  pip install -r adversarial/requirements.txt
  ```
- **Model download**: The first run of `dataset_creation.py` will automatically download the `Qwen/Qwen3-32B` model weights (~64GB) from HuggingFace Hub. Ensure you have sufficient disk space and network access. Subsequent runs use cached weights.

> **Note:** No API tokens or `.env` files are needed. The LLM runs entirely locally.

### Step 1: Create the Dataset

Generate the clean rendered images, crop targeted lines, and compile the unified `dataset_manifest.json` metadata catalog:

```bash
python adversarial/dataset_creation.py
```

### Step 2: Run Attacks for an OCR Engine

To run all attack configurations for a specific engine, use:

```bash
python adversarial/run_ocr.py <engine_name>
```

Where `<engine_name>` is one of: `easyocr`, `tesseract`, `gotocr`, or `trocr`.

Alternatively, use the dedicated engine-specific wrappers:

```bash
# Run attacks on EasyOCR
python adversarial/run_easyocr.py

# Run attacks on Tesseract
python adversarial/run_tesseract.py

# Run attacks on GOT-OCR
python adversarial/run_gotocr.py

# Run attacks on TrOCR
python adversarial/run_trocr.py
```

**Requirements:** NVIDIA A100 80GB GPU (or equivalent with ≥64GB VRAM) for local LLM inference.
