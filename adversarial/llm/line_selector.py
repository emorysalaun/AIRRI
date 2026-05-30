"""LLM-based semantic line selection using local HuggingFace transformers."""

import json
import logging
import re
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

logger = logging.getLogger(__name__)


class LLMLineSelector:
    """Selects the most semantically important lines from assignment text using a local LLM."""

    def __init__(
        self,
        model: str = "Qwen/Qwen3-32B",
        device: str | None = None,
        torch_dtype: torch.dtype = torch.bfloat16,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        cache_dir: str | None = None,
    ):
        self.model_name = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache_dir = cache_dir

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Loading tokenizer for {model}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model,
            cache_dir=self.cache_dir
        )

        logger.info(f"Loading model {model} (dtype={torch_dtype}) onto {self.device}...")
        self.model = AutoModelForCausalLM.from_pretrained(
            model,
            torch_dtype=torch_dtype,
            device_map=self.device,
            cache_dir=self.cache_dir,
        )
        self.model.eval()
        logger.info(f"Model {model} loaded successfully.")

    def select_important_lines(self, ground_truth: str) -> list[str]:
        """Ask the LLM to identify the most important lines/sentences needed to do the assignment.

        Returns:
            A list of important lines/sentences exactly as they appear in ground_truth.

        Raises:
            RuntimeError: If inference fails or selects no valid lines.
        """
        ground_truth = ground_truth.strip()
        if not ground_truth:
            return []

        prompt = f"""You are an expert document analysis AI. Your objective is to extract the most critical information from a given document, whether it is a general reading passage or an academic assignment.

### CRITICAL EXTRACTION GOALS
Identify and extract the exact lines or sentences that contain the core substance or actionable requirements of the text. These excerpts DO NOT need to be consecutive.

* For Academic Assignments (Task Execution): Extract the absolute minimum set of verbatim instructions an AI would need to complete the assignment perfectly. Focus exclusively on:
  - The specific task, problem, or topic to be addressed.
  - Required deliverables.
  - Strict constraints (format, length, citation style, language, required sources).
  - Specific grading or evaluation criteria.
* For General Documents (Core Message): Extract the sentences that encapsulate the primary thesis, critical facts, or main conclusions.

### EXCLUSION CRITERIA (DO NOT EXTRACT)
Ignore all text related to:
* Administrative information, due dates, or course logistics.
* Submission procedures (e.g., "Upload to Canvas", "File naming conventions").
* Generic academic integrity statements or boilerplate policies.
* Instructor contact information or office hours.
* Filler text or introductory fluff.

### STRICT CONSTRAINTS
1. EXACT SUBSTRING MATCH REQUIRED: You MUST copy the text exactly, character-for-character, from the source document. Do NOT alter whitespace, capitalization, punctuation, or fix typos.
2. NO MODIFICATIONS: Do not paraphrase, summarize, combine, or truncate excerpts. Any extracted string that is not a literal substring of the source text will cause a system failure.
3. MAXIMUM LENGTH: The total length of the extracted text MUST NOT exceed 50% of the original document's length. Prioritize ruthlessly.
4. JSON OUTPUT ONLY: Return ONLY a valid JSON array of strings. Do not include explanations, conversational text, or Markdown formatting (do not use ```json). If no critical information exists, return an empty array [].

Source Document:
{ground_truth}
"""

        messages = [
            {"role": "user", "content": prompt}
        ]

        for attempt in range(self.max_retries):
            try:
                # Apply chat template with thinking disabled for clean JSON output
                input_text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
                inputs = self.tokenizer(input_text, return_tensors="pt").to(self.device)

                with torch.no_grad():
                    output_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=4096,
                        do_sample=False,
                    )

                # Decode only the newly generated tokens (skip prompt tokens)
                generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
                response_text = self.tokenizer.decode(
                    generated_ids, skip_special_tokens=True
                )

                if not response_text:
                    raise ValueError("LLM returned an empty response.")

                lines = self._parse_json_response(response_text)

                valid_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    if line_stripped in ground_truth:
                        valid_lines.append(line_stripped)
                    else:
                        matched = self._find_fuzzy_match(line_stripped, ground_truth)
                        if matched:
                            valid_lines.append(matched)
                        else:
                            logger.warning(
                                f"LLM selected line not found in ground truth: {repr(line_stripped)}"
                            )

                if not valid_lines:
                    raise ValueError("LLM response did not contain any valid lines that matched the text.")

                return valid_lines

            except Exception as e:
                logger.error(
                    f"LLM inference or parsing failed on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    raise RuntimeError(f"LLM inference failed permanently: {e}")

        raise RuntimeError("LLM inference failed and no response was received.")

    def _parse_json_response(self, response_text: str) -> list[str]:
        """Parse JSON array from LLM response, stripping markdown fences and thinking tokens."""
        clean_text = response_text.strip()

        # Strip <think>...</think> blocks (defense-in-depth for Qwen3)
        clean_text = re.sub(
            r"<think>.*?</think>", "", clean_text, flags=re.DOTALL
        ).strip()

        # Strip markdown code fences
        if clean_text.startswith("```"):
            first_newline = clean_text.find("\n")
            if first_newline != -1:
                clean_text = clean_text[first_newline:].strip()
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3].strip()

        data = json.loads(clean_text)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise ValueError("LLM response did not contain a JSON array.")

    def _find_fuzzy_match(self, line: str, ground_truth: str) -> str | None:
        """Find a substring in ground_truth that matches line, ignoring whitespace/punctuation/case.

        Handles multi-line spans by first checking against the full normalized text,
        then falling back to per-line matching.
        """
        normalized_line = "".join(c.lower() for c in line if c.isalnum())
        if not normalized_line:
            return None

        # First: try matching against the full normalized text (handles multi-line spans)
        normalized_full = "".join(c.lower() for c in ground_truth if c.isalnum())
        pos = normalized_full.find(normalized_line)
        if pos != -1:
            # Map back to original text: find the original character range
            orig_start = None
            orig_end = None
            alnum_count = 0
            for i, ch in enumerate(ground_truth):
                if ch.isalnum():
                    if alnum_count == pos and orig_start is None:
                        orig_start = i
                    alnum_count += 1
                    if alnum_count == pos + len(normalized_line):
                        orig_end = i + 1
                        break
            if orig_start is not None and orig_end is not None:
                return ground_truth[orig_start:orig_end].strip()

        # Fallback: check individual lines
        lines = [l.strip() for l in ground_truth.splitlines() if l.strip()]
        for l in lines:
            norm_l = "".join(c.lower() for c in l if c.isalnum())
            if normalized_line in norm_l:
                return l

        return None

    def cleanup(self):
        """Free GPU memory by deleting the model and tokenizer."""
        if hasattr(self, "model"):
            del self.model
        if hasattr(self, "tokenizer"):
            del self.tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
