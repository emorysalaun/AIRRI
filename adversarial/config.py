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
                "iterations": 150,
                "pc": 0.85,
                "pm": 0.15,
                "pop_size": 10,
                "seed": 42,
            },
            "adba": {
                "budget": 2500,
                "init_dir": 1,
                "offspring_n": 8,
                "binary_mode": 0,
            },
            "rays": {
                "query_limit": 2000,
            },
            "surfree": {
                "init": {"steps": 75, "max_queries": 2500},
                "run": {},
            },
            "l0_pgd": {
                "n_restarts": 1,
                "num_steps": 100,
                "step_size": 120.0 / 255.0,
                "random_start": False,
            },
            "l0_sigma_pgd": {
                "n_restarts": 1,
                "num_steps": 100,
                "step_size": 120.0 / 255.0,
                "random_start": False,
            },
            "l0_linf_pgd": {
                "n_restarts": 1,
                "num_steps": 100,
                "step_size": 120.0 / 255.0,
                "random_start": False,
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
