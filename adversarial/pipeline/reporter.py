
"""Pipeline result reporting — score logging and CSV output."""

import csv
from pathlib import Path


class PipelineReporter:
    """Manages appending results directly to a CSV file."""

    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)
        self.fieldnames = [
            "image_name",
            "engine",
            "eps",
            "attack",
            "eval_scope",
            "target_line",
            "cer",
            "wer",
        ]
        # Write header if file does not exist
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def record_row(
        self,
        image_name: str,
        engine_name: str,
        eps: float,
        attack_name: str,
        eval_scope: str,
        target_line: str,
        cer: float,
        wer: float,
    ):
        """Record a single score row and write it immediately to disk."""
        img_name = (
            image_name.replace(".txt", ".png")
            if image_name.endswith(".txt")
            else image_name
        )
        row = {
            "image_name": img_name,
            "engine": engine_name,
            "eps": eps,
            "attack": attack_name,
            "eval_scope": eval_scope,
            "target_line": target_line,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
        }
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerow(row)
