"""LLM-based semantic line selection using Hugging Face Inference API."""

import json
import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

# Load .env file containing HF_TOKEN
_ADV_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_ADV_DIR / ".env")


class LLMLineSelector:
    """Selects the most semantically important lines from assignment text using LLM."""

    def __init__(
        self,
        model: str = "google/gemma-4-31B-it:fastest",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Check API token
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            logger.warning("HF_TOKEN environment variable not set. LLM requests will fail unless API is public.")
        
        self.client = InferenceClient(api_key=hf_token)

    def select_important_lines(self, ground_truth: str) -> list[str]:
        """Ask the LLM to identify the most important lines/sentences needed to do the assignment.

        Returns:
            A list of important lines/sentences exactly as they appear in ground_truth.
            If the API call fails or returns invalid results, falls back to returning
            all non-empty lines of ground_truth.
        """
        ground_truth = ground_truth.strip()
        if not ground_truth:
            return []

        prompt = f"""You are analyzing an academic assignment sheet.

Your goal is to identify the exact lines or sentences that contain the information an AI system would need in order to complete the assignment.
The lines DO NOT need to be consecutive. They may come from completely different parts of the document.

Think from the perspective of an LLM attempting to perform the assignment. Select the smallest set of verbatim excerpts that collectively answer questions such as:
- What is the student being asked to do?
- What content, topic, problem, or question must be addressed?
- What deliverables are required?
- What constraints must the response satisfy (format, length, citation style, language, sources, structure, etc.)?
- What evaluation criteria define success?

Prioritize instructions that directly determine how the assignment should be completed.

Do NOT prioritize:
- Administrative information
- Course logistics
- Submission procedures
- Due dates
- Instructor contact information
- Generic academic integrity statements

Selection criteria:
1. Choose only lines that are essential for completing the assignment.
2. If removing a line would significantly reduce an LLM's ability to perform the task correctly, include it.
3. Prefer task-defining instructions over administrative details.
4. Extract exact verbatim text only.
5. Do not paraphrase, summarize, or combine excerpts.

Return ONLY a JSON array of strings, where each string is an exact excerpt from the original assignment text.

Assignment text:
{ground_truth}
"""

        messages = [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]

        response_text = ""
        for attempt in range(self.max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=1000,
                )
                response_text = completion.choices[0].message.content
                if response_text:
                    break
            except Exception as e:
                logger.warning(
                    f"LLM API call failed on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    logger.error("LLM API call failed. Falling back to all lines.")
                    return self._fallback_lines(ground_truth)

        if not response_text:
            return self._fallback_lines(ground_truth)

        # Parse the JSON response
        try:
            lines = self._parse_json_response(response_text)
        except Exception as e:
            logger.warning(
                f"Failed to parse LLM response as JSON. Response was: {response_text}. Error: {e}"
            )
            return self._fallback_lines(ground_truth)

        # Validate that each selected line is actually a substring of ground_truth
        valid_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if line_stripped in ground_truth:
                valid_lines.append(line_stripped)
            else:
                # Try a slightly relaxed search (e.g. normalize spaces)
                matched = self._find_fuzzy_match(line_stripped, ground_truth)
                if matched:
                    valid_lines.append(matched)
                else:
                    logger.warning(
                        f"LLM selected line not found in ground truth: {repr(line_stripped)}"
                    )

        if not valid_lines:
            logger.warning("LLM response did not contain any valid lines. Falling back.")
            return self._fallback_lines(ground_truth)

        return valid_lines

    def _fallback_lines(self, ground_truth: str) -> list[str]:
        """Graceful fallback: returns all non-empty lines from the ground truth."""
        return [line.strip() for line in ground_truth.splitlines() if line.strip()]

    def _parse_json_response(self, response_text: str) -> list[str]:
        """Parse JSON array from LLM response, stripping markdown fences if present."""
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            # Strip start fence
            first_newline = clean_text.find("\n")
            if first_newline != -1:
                clean_text = clean_text[first_newline:].strip()
            # Strip end fence
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3].strip()

        data = json.loads(clean_text)
        if isinstance(data, list):
            return [str(item) for item in data]
        raise ValueError("LLM response did not contain a JSON array.")

    def _find_fuzzy_match(self, line: str, ground_truth: str) -> str | None:
        """Find a substring in ground_truth that matches line, ignoring whitespace differences."""
        # Simple whitespace normalization comparison
        normalized_line = "".join(line.split())
        if not normalized_line:
            return None

        # Slide a window over ground_truth split lines or words to see if we get a match
        lines = [l.strip() for l in ground_truth.splitlines() if l.strip()]
        for l in lines:
            if normalized_line in "".join(l.split()):
                return l
        return None
