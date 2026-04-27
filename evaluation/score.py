import re
from pathlib import Path


def levenshtein(a: str, b: str) -> int:
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new_dp = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            new_dp.append(min(
                dp[j] + 1,
                new_dp[j - 1] + 1,
                dp[j - 1] + cost
            ))
        dp = new_dp
    return dp[-1]

def tokenize_words(text: str, ignore_case: bool = True) -> list[str]:
    if ignore_case:
        text = text.lower()

    return re.findall(r"\S+", text)


def normalize_text(text: str, ignore_case: bool = True) -> str:
    cleaned = re.sub(r"\s+", "", text)
    if ignore_case:
        cleaned = cleaned.lower()
    return cleaned


def evaluate_text_pair(predicted: str, ground_truth: str, ignore_case: bool = True) -> float:
    pred_clean = normalize_text(predicted, ignore_case=ignore_case)
    gt_clean = normalize_text(ground_truth, ignore_case=ignore_case)

    if not gt_clean:
        return 100.0 if not pred_clean else 0.0

    dist = levenshtein(gt_clean, pred_clean)
    accuracy = (1 - dist / len(gt_clean)) * 100
    return max(0.0, accuracy)

def evaluate_text_pair_wer(predicted: str, ground_truth: str, ignore_case: bool = True) -> float:
    pred_tokens = tokenize_words(predicted, ignore_case)
    gt_tokens = tokenize_words(ground_truth, ignore_case)

    if not gt_tokens:
        return 100.0 if not pred_tokens else 0.0

    dist = levenshtein(gt_tokens, pred_tokens)
    accuracy = (1 - dist / len(gt_tokens)) * 100
    return max(0.0, accuracy)


def evaluate_ocr_folder(results_dir, ground_truth, ignore_case: bool = True):
    """
    Old single-ground-truth version.
    Returns a dict: {filename: accuracy_percent}
    """
    results_dir = Path(results_dir)
    scores = {}

    for txt_file in results_dir.glob("*.txt"):
        ocr_output = txt_file.read_text(encoding="utf-8")
        scores[txt_file.name] = evaluate_text_pair(
            ocr_output,
            ground_truth,
            ignore_case=ignore_case,
        )

    return scores


def evaluate_ocr_folder_with_manifest(results_dir, manifest, ignore_case: bool = True):
    """
    Manifest version.
    Manifest format:
    [
      {
        "image_name": "clean.png",
        "ground_truth": "..."
      }
    ]

    Returns a dict: {txt_filename: accuracy_percent}
    """
    results_dir = Path(results_dir)
    scores = {}

    for item in manifest:
        image_name = item["image_name"]
        ground_truth = item["ground_truth"]

        txt_name = Path(image_name).with_suffix(".txt").name
        txt_path = results_dir / txt_name

        if not txt_path.exists():
            continue

        ocr_output = txt_path.read_text(encoding="utf-8")
        scores[txt_name] = evaluate_text_pair(
            ocr_output,
            ground_truth,
            ignore_case=ignore_case,
        )

    return scores

def evaluate_ocr_folder_with_manifest_wer(results_dir, manifest, ignore_case: bool = True):
    results_dir = Path(results_dir)
    scores = {}

    for item in manifest:
        image_name = item["image_name"]
        ground_truth = item["ground_truth"]

        txt_name = Path(image_name).with_suffix(".txt").name
        txt_path = results_dir / txt_name

        if not txt_path.exists():
            continue

        ocr_output = txt_path.read_text(encoding="utf-8")
        scores[txt_name] = evaluate_text_pair_wer(
            ocr_output,
            ground_truth,
            ignore_case=ignore_case,
        )

    return scores

