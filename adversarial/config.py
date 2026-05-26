from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    attacks: list[str] = field(
        default_factory=lambda: ["smoo", "adba", "rays", "surfree"]
    )
    attack_eps: dict = field(
        default_factory=lambda: {
            "adba": [4 / 255, 8 / 255, 16 / 255],
            "rays": [4 / 255, 8 / 255, 16 / 255],
            "surfree": [2, 3, 5],
            "smoo": [10, 20],
        }
    )
    engines: list[str] = field(
        default_factory=lambda: ["easyocr", "tesseract", "gotocr", "trocr"]
    )

    attack_configs: dict = field(
        default_factory=lambda: {
            "smoo": {
                "iterations": 500,  # 500 gens × pop_size=10 ≈ 5000 queries
                "pc": 0.80,  # crossover: balanced exploration
                "pm": 0.20,  # mutation: diverse pixel candidates
                "pop_size": 10,  # 10 candidates/generation
                "seed": 42,
            },
            "adba": {
                "budget": 10000,  # 10K queries
                "init_dir": 1,  # positive initial direction
                "offspring_n": 10,  # 10 offspring for fine-grained boundary
                "binary_mode": 0,
            },
            "rays": {
                "query_limit": 10000,  # 10K queries
            },
            "surfree": {
                "init": {
                    "steps": 200,  # 200 optimization steps
                    "max_queries": 10000,  # 10K queries for L2 minimization
                },
                "run": {},
            },
        }
    )
    cer_threshold: float = 50.0
    dataset_root: Path = Path(__file__).resolve().parent.parent / "dataset"
    datasets: list[dict] = field(
        default_factory=lambda: [
            {
                "name": "UCONN",
                "manifest": "UCONN/manifest.json",
                "renders": "UCONN/clean_renders",
            },
            {
                "name": "8and12_12",
                "manifest": "8and12/12/manifest.json",
                "renders": "8and12/12/clean_renders",
            },
        ]
    )
    output_dir: Path = Path(__file__).resolve().parent / "output"

    # LLM-based line selection configuration
    llm_model: str = "google/gemma-4-31B-it:fastest"
    llm_max_retries: int = 3

    # Rendering configuration
    render_font_path: str | None = None
    render_font_size: int = 12
    render_wrap_width: int = 90
    render_margin_x: int = 15
    render_margin_top: int = 16
    render_margin_bottom: int = 17
    render_line_padding: int = 5
    render_bg_color: str = "white"
    render_text_color: str = "black"

    # Stitching and evaluation configurations
    stitch_mode: str = "hard"  # "hard" mask compositing
    eval_mode: str = "both"    # "full", "target", or "both"

