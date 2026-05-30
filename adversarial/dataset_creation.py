"""Dataset creation entry point — generates images, clips, and manifests."""

import json
import sys
from pathlib import Path

_ADV_DIR = str(Path(__file__).resolve().parent)
if _ADV_DIR not in sys.path:
    sys.path.insert(0, _ADV_DIR)

from config import PipelineConfig
from utils.logger import ExperimentLogger
from renderer.text_renderer import TextRenderer
from region.matcher import match_semantic_to_visual
from llm.line_selector import LLMLineSelector
from data.handler import load_manifest, filter_clean_manifest, save_dataset_manifest


def create_dataset(config: PipelineConfig) -> Path:
    """Iterate through all source data, perform LLM line selection, render clean images,

    crop individual lines, and compile the metadata manifest for downstream attacks.

    Raises on LLM failure or empty matching — no fallbacks.
    """
    log_dir = config.output_dir / "logs"
    logger = ExperimentLogger("dataset_creation", str(log_dir))
    logger.section("AIRRI Dataset Creation Stage")

    llm_selector = LLMLineSelector(
        model=config.llm_model, 
        cache_dir=config.llm_cache_dir
    )
    renderer = TextRenderer(
        font_path=config.render_font_path,
        font_size=config.render_font_size,
        wrap_width=config.render_wrap_width,
        margin_x=config.render_margin_x,
        margin_top=config.render_margin_top,
        margin_bottom=config.render_margin_bottom,
        line_padding=config.render_line_padding,
        bg_color=config.render_bg_color,
        text_color=config.render_text_color,
    )

    dataset_manifest_data = {"datasets": []}

    for ds in config.datasets:
        ds_name = ds["name"]
        manifest_path = config.dataset_root / ds["manifest"]

        logger.section(f"Processing Dataset: {ds_name}")
        logger.info(f"Manifest path: {manifest_path}")

        manifest = load_manifest(manifest_path)
        manifest = filter_clean_manifest(manifest)
        logger.info(f"Loaded {len(manifest)} clean manifest entries")

        ds_output_dir = config.output_dir / ds_name
        clean_renders_dir = ds_output_dir / "clean_renders"
        clean_renders_dir.mkdir(parents=True, exist_ok=True)

        llm_cache_dir = ds_output_dir / "llm_selections"
        llm_cache_dir.mkdir(parents=True, exist_ok=True)

        ds_items = []

        for idx, item in enumerate(manifest, 1):
            img_name = item["image_name"]
            base_name = Path(img_name).stem
            logger.info(f"[{idx}/{len(manifest)}] Processing {img_name}...")

            # 1. LLM Selection
            cache_path = llm_cache_dir / f"{base_name}.json"
            if cache_path.exists():
                with cache_path.open("r", encoding="utf-8") as f:
                    selected_lines = json.load(f)
                logger.info("  Loaded LLM selections from cache")
            else:
                selected_lines = llm_selector.select_important_lines(item["ground_truth"])
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(selected_lines, f, indent=2)
                logger.info("  Queried and cached LLM selections")

            if not selected_lines:
                raise ValueError(f"LLM line selection returned no lines for {img_name}")

            # 2. Rendering
            rendered = renderer.render(item["ground_truth"], img_name)
            rendered.image.save(clean_renders_dir / img_name)

            # 3. Matching
            matched_regions = match_semantic_to_visual(selected_lines, rendered)
            if not matched_regions:
                raise ValueError(
                    f"Zero matched regions found for {img_name}. "
                    "All LLM selected lines failed to align with visual lines."
                )

            # 4. Crop & Save
            crops_dir = clean_renders_dir / "crops" / base_name
            crops_dir.mkdir(parents=True, exist_ok=True)

            serializable_regions = []
            for region in matched_regions:
                # Crop lines in this region
                for vl in region.visual_lines:
                    x1, y1, x2, y2 = vl.bbox
                    crop_img = rendered.image.crop((x1, y1, x2, y2))
                    crop_img.save(crops_dir / f"line_{vl.line_index:02d}.png")

                serializable_regions.append({
                    "semantic_line": region.semantic_line,
                    "union_bbox": list(region.union_bbox),
                    "per_line_gt": region.per_line_gt,
                    "visual_lines": [
                        {
                            "text": vl.text,
                            "bbox": list(vl.bbox),
                            "line_index": vl.line_index
                        }
                        for vl in region.visual_lines
                    ]
                })

            ds_items.append({
                "image_name": img_name,
                "ground_truth": item["ground_truth"],
                "full_text": rendered.full_text,
                "llm_selections": selected_lines,
                "matched_regions": serializable_regions,
            })

        dataset_manifest_data["datasets"].append({
            "name": ds_name,
            "items": ds_items
        })

    manifest_path = config.dataset_manifest_path
    save_dataset_manifest(dataset_manifest_data, manifest_path)
    logger.section(f"Dataset preparation complete. Manifest saved to {manifest_path}")
    return manifest_path


if __name__ == "__main__":
    config = PipelineConfig()
    try:
        create_dataset(config)
    except Exception as e:
        print(f"Error during dataset creation: {e}", file=sys.stderr)
        sys.exit(1)
