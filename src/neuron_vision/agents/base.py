"""
Base class for all Neuron Vision Display agents.
Uses Google ADK patterns with Vertex AI Gemini 2.5 Pro as the model backend.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import vertexai
from pydantic import BaseModel
from vertexai.generative_models import GenerationConfig, GenerativeModel, Image, Part

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Model configuration — us-central1 as required by the ТЗ
_GEMINI_MODEL = "gemini-2.5-pro-preview-05-06"
_REGION = "us-central1"

_vertexai_initialized = False


def _ensure_vertexai() -> None:
    global _vertexai_initialized
    if not _vertexai_initialized:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise EnvironmentError(
                "GOOGLE_CLOUD_PROJECT environment variable is not set. "
                "Copy .env.example to .env and fill in your project ID."
            )
        vertexai.init(project=project, location=_REGION)
        _vertexai_initialized = True


class NeuronVisionAgent(ABC, Generic[T]):
    """
    Abstract base for every agent in the RomeoFlexVision brigade.

    Each concrete agent specifies:
      - ``name``        : unique identifier used in Evidence Log
      - ``instruction`` : system-level prompt sent with every request
      - ``output_model``: Pydantic v2 model class — enforces structured output
    """

    name: str
    instruction: str
    output_model: type[T]

    def __init__(self) -> None:
        _ensure_vertexai()
        self._model = GenerativeModel(
            _GEMINI_MODEL,
            system_instruction=self.instruction,
        )
        logger.info("Agent '%s' initialised with model %s", self.name, _GEMINI_MODEL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, image_bytes: bytes, context: dict | None = None) -> T:
        """
        Run the agent against a PCB image.

        Args:
            image_bytes: Raw JPEG/PNG bytes of the board photo.
            context:     Optional dict with upstream agent results to inject
                         into the prompt (e.g., triage risk zones).

        Returns:
            A validated Pydantic instance of ``output_model``.
        """
        image_part = Part.from_data(image_bytes, mime_type=self._detect_mime(image_bytes))
        prompt = self._build_prompt(context or {})

        logger.info("Agent '%s': calling Gemini 2.5 Pro …", self.name)

        # Primary path: response_schema with Pydantic model
        try:
            response = self._model.generate_content(
                [image_part, prompt],
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=self.output_model,
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )
            result = self.output_model.model_validate_json(response.text)
        except Exception as exc:
            # Fallback: ask the model to produce JSON matching the schema
            logger.warning(
                "Agent '%s': structured output failed (%s), falling back to schema-in-prompt",
                self.name,
                exc,
            )
            result = self._fallback_run(image_part, prompt)

        logger.info("Agent '%s': completed → %s", self.name, result.__class__.__name__)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, context: dict) -> str:
        """Override in subclasses to inject upstream context into the prompt."""
        return ""

    def _fallback_run(self, image_part: Part, prompt: str) -> T:
        schema_json = json.dumps(self.output_model.model_json_schema(), indent=2)
        fallback_prompt = (
            f"{prompt}\n\n"
            "Respond ONLY with a single valid JSON object that conforms exactly "
            f"to the following JSON Schema:\n```json\n{schema_json}\n```"
        )
        response = self._model.generate_content(
            [image_part, fallback_prompt],
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )
        # Strip markdown fences if present
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return self.output_model.model_validate_json(text.strip())

    @staticmethod
    def _detect_mime(data: bytes) -> str:
        """Detect JPEG vs PNG from magic bytes."""
        if data[:4] == b"\x89PNG":
            return "image/png"
        return "image/jpeg"
