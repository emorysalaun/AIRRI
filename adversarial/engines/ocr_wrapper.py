"""OCR engine wrapper — bridges black-box attacks with OCR inference.

Wraps OCR engines as 2-class pseudo-classifiers so standard
adversarial attack wrappers (which expect model(x).argmax(1))
can query OCR engines.

    Class 0 = misread   (accuracy below threshold)
    Class 1 = correct   (accuracy at or above threshold)
"""

import sys
import tempfile
import shutil
from pathlib import Path

import torch
from PIL import Image

# Ensure evaluation/ is importable (defensive; entry points also set this)
_EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation"
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

from score import evaluate_text_pair

# Import evaluation engines by absolute path to avoid collision with
# adversarial/engines/ (this package).
import importlib.util

def _import_eval_engine(module_name, filename):
    spec = importlib.util.spec_from_file_location(
        module_name, _EVAL_DIR / "engines" / filename
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_easyocr_mod = _import_eval_engine("easyocr_engine", "easyocr_engine.py")
_tesseract_mod = _import_eval_engine("tesseract_engine", "tesseract_engine.py")
_gotocr_mod = _import_eval_engine("gotocr_engine", "gotocr_engine.py")
_trocr_mod = _import_eval_engine("trocr_engine", "trocr_engine.py")

run_easyocr_folder = _easyocr_mod.run_easyocr_folder
run_tesseract_folder = _tesseract_mod.run_tesseract_folder
run_gotocr_folder = _gotocr_mod.run_gotocr_folder
run_trocr_folder = _trocr_mod.run_trocr_folder

ENGINE_FNS = {
    "easyocr": lambda in_dir, out_dir: run_easyocr_folder(
        input_dir=in_dir,
        output_dir=out_dir,
        languages=["en"],
        gpu=None,
        paragraph=True,
        use_sorted_reading_order=False,
    ),
    "tesseract": lambda in_dir, out_dir: run_tesseract_folder(
        input_dir=in_dir,
        output_dir=out_dir,
        lang="eng",
        psm=6,
        oem=3,
        timeout=10.0,
    ),
    "gotocr": lambda in_dir, out_dir: run_gotocr_folder(
        input_dir=in_dir,
        output_dir=out_dir,
        model_name="stepfun-ai/GOT-OCR-2.0-hf",
        device=None,
        max_new_tokens=1024,
    ),
    "trocr": lambda in_dir, out_dir: run_trocr_folder(
        input_dir=in_dir,
        output_dir=out_dir,
    ),
}


def _tensor_to_pil(tensor):
    """NCHW float [0,1] tensor → PIL Image. Handles single image or batch."""
    if tensor.dim() == 4:
        tensor = tensor[0]
    arr = (tensor.detach().cpu().clamp(0, 1) * 255).byte()
    arr = arr.permute(1, 2, 0).numpy()
    if arr.shape[2] == 1:
        arr = arr.squeeze(2)
    return Image.fromarray(arr)


def _run_ocr_on_image(pil_image, engine_name, work_dir):
    """Save image to work_dir, run OCR engine, return extracted text."""
    in_dir = Path(work_dir) / "input"
    out_dir = Path(work_dir) / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    img_path = in_dir / "query.png"
    pil_image.save(img_path)

    ENGINE_FNS[engine_name](in_dir, out_dir)

    txt_path = out_dir / "query.txt"
    if txt_path.exists():
        return txt_path.read_text(encoding="utf-8")
    return ""


class OCRModelWrapper:
    """Wraps an OCR engine as a 2-class pseudo-classifier for black-box attacks.

    Class 0 = misread  (accuracy below threshold)
    Class 1 = correct  (accuracy at or above threshold)

    Attacks set true_label=1 so they try to force misreads.
    """

    def __init__(self, engine_name, ground_truth, cer_threshold=50.0):
        if engine_name not in ENGINE_FNS:
            raise ValueError(
                f"Unknown engine '{engine_name}'. Available: {list(ENGINE_FNS)}"
            )
        self.engine_name = engine_name
        self.ground_truth = ground_truth
        self.cer_threshold = cer_threshold
        self._query_count = 0
        self._work_dir = tempfile.mkdtemp(prefix="ocr_wrapper_")

    def __call__(self, image_tensor):
        """Run OCR on image_tensor and return 2-class pseudo-logits.

        Args:
            image_tensor: (N,C,H,W) or (C,H,W) float tensor in [0,1]

        Returns:
            torch.Tensor of shape (N, 2)
        """
        if image_tensor.dim() == 3:
            image_tensor = image_tensor.unsqueeze(0)

        batch_size = image_tensor.shape[0]
        logits = torch.zeros(batch_size, 2)

        for i in range(batch_size):
            pil_img = _tensor_to_pil(image_tensor[i])
            ocr_text = _run_ocr_on_image(pil_img, self.engine_name, self._work_dir)
            accuracy = evaluate_text_pair(ocr_text, self.ground_truth)
            self._query_count += 1

            if accuracy >= self.cer_threshold:
                logits[i] = torch.tensor([0.0, 1.0])  # class 1: correct
            else:
                logits[i] = torch.tensor([1.0, 0.0])  # class 0: misread

        return logits.to(image_tensor.device)

    def eval(self):
        return self

    def cleanup(self):
        shutil.rmtree(self._work_dir, ignore_errors=True)

    @property
    def query_count(self):
        return self._query_count

    def __del__(self):
        self.cleanup()
