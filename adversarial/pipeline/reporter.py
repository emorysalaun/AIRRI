"""Pipeline result reporting — score logging and CSV output."""

import csv
from pathlib import Path


class PipelineReporter:
    """Buffers per-image scores and writes them to structured logs and CSV."""

    def __init__(self, logger):
        self.logger = logger
        self.all_rows = []

    def record_scores(
        self, engine_name: str, eps: float, cer_scores: dict, wer_scores: dict
    ):
        """Log score summary and buffer rows for CSV output."""
        if not cer_scores:
            self.logger.warning("No scores computed")
            return

        cer_vals = list(cer_scores.values())
        wer_vals = list(wer_scores.values())
        avg_cer = sum(cer_vals) / len(cer_vals)
        avg_wer = sum(wer_vals) / len(wer_vals) if wer_vals else 0.0

        self.logger.info(f"Average CER: {avg_cer:.2f}%")
        self.logger.info(f"Average WER: {avg_wer:.2f}%")
        self.logger.info(f"Scored {len(cer_scores)} images")

        for name in cer_scores:
            self.logger.debug(
                f"  {name}: CER={cer_scores[name]:.2f}% WER={wer_scores.get(name, 0):.2f}%"
            )

            img_name = name.replace(".txt", ".png") if name.endswith(".txt") else name
            self.all_rows.append(
                {
                    "image_name": img_name,
                    "engine": engine_name,
                    "eps": eps,
                    "cer": round(cer_scores[name], 4),
                    "wer": round(wer_scores.get(name, 0.0), 4),
                }
            )

    def write_csv(self, csv_path: Path):
        """Flush buffered scores to CSV and clear the buffer."""
        if not self.all_rows:
            return

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["image_name", "engine", "eps", "cer", "wer"]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_rows)

        self.logger.info(f"Results CSV → {csv_path}")
        self.all_rows.clear()
