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
                "iterations": 500,      # 500 gens × pop_size=10 ≈ 5000 queries
                "pc": 0.80,             # crossover: balanced exploration
                "pm": 0.20,             # mutation: diverse pixel candidates
                "pop_size": 10,         # 10 candidates/generation
                "seed": 42,
            },
            "adba": {
                "budget": 10000,        # 10K queries — exhaustive boundary search
                "init_dir": 1,          # positive initial direction
                "offspring_n": 10,      # 10 offspring for fine-grained boundary
                "binary_mode": 0,
            },
            "rays": {
                "query_limit": 10000,   # 10K queries — deep sign search
            },
            "surfree": {
                "init": {
                    "steps": 200,       # 200 optimization steps
                    "max_queries": 10000,  # 10K queries for L2 minimization
                },
                "run": {},
            },
            "l0_pgd": {
                "n_restarts": 5,        # 5 random restarts for best L0 solution
                "num_steps": 500,       # 500 PGD steps per restart
                "step_size": 120.0 / 255.0,
                "random_start": True,   # randomize for diversity across restarts
            },
            "l0_sigma_pgd": {
                "n_restarts": 5,
                "num_steps": 500,
                "step_size": 120.0 / 255.0,
                "random_start": True,
            },
            "l0_linf_pgd": {
                "n_restarts": 5,
                "num_steps": 500,
                "step_size": 120.0 / 255.0,
                "random_start": True,
            },
        }
    )
    cer_threshold: float = 50.0
    manifest_path: Path = (
        Path(__file__).resolve().parent.parent / "evaluation" / "data" / "manifest.json"
    )
    renders_dir: Path = (
        Path(__file__).resolve().parent.parent / "evaluation" / "data" / "renders"
    )
    output_dir: Path = Path(__file__).resolve().parent / "output"
