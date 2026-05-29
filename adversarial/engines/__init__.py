"""adversarial.engines — OCR engine wrappers for black-box attacks."""

from .ocr_wrapper import OCRModelWrapper, ENGINE_FNS, run_ocr_on_pil

__all__ = ["OCRModelWrapper", "ENGINE_FNS", "run_ocr_on_pil"]
