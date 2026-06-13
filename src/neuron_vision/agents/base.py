"""
Base class for all Neuron Vision Display agents.
Uses Google ADK patterns with Vertex AI Gemini 2.5 Pro as the model backend.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from abc import ABC
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    import vertexai
    from vertexai.generative_models import GenerationConfig, GenerativeModel, Part
else:
    try:  # Optional: demo mode and orchestration tests run without Vertex AI.
        import vertexai
        from vertexai.generative_models import GenerationConfig, GenerativeModel, Part
    except ImportError:  # pragma: no cover - exercised only in minimal envs
        vertexai = None
        GenerationConfig = GenerativeModel = Part = None

__all__ = [
    "GenerationConfig",
    "GenerativeModel",
    "NeuronVisionAgent",
    "Part",
    "is_valid_project_id",
]

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Model configuration — us-central1 as required by the ТЗ.
# The retired preview ID returns 404 on Vertex AI; use the current stable model.
_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# ```json ... ``` (or bare ``` ... ```) block anywhere in the response.
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)

_vertexai_initialized = False
_vertexai_init_lock = threading.Lock()
_VERTEX_SCHEMA_KEYS = {
    "anyOf",
    "default",
    "description",
    "enum",
    "example",
    "format",
    "items",
    "maxItems",
    "maxLength",
    "maxProperties",
    "maximum",
    "minItems",
    "minLength",
    "minProperties",
    "minimum",
    "nullable",
    "pattern",
    "properties",
    "propertyOrdering",
    "required",
    "title",
    "type",
}


# GCP project IDs: 6-30 chars, lowercase letters, digits and hyphens,
# starting with a letter and not ending with a hyphen.
_PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")


def is_valid_project_id(project_id: str) -> bool:
    """Check that a string is a plausible GCP project ID."""
    return bool(_PROJECT_ID_RE.fullmatch(project_id))


def _ensure_vertexai(project: str | None = None) -> None:
    """Initialize Vertex AI once per process.

    ``project`` takes precedence over the ``GOOGLE_CLOUD_PROJECT`` environment
    variable, so callers (e.g. the UI) can pass a validated value instead of
    mutating process-wide environment state.
    """
    global _vertexai_initialized
    with _vertexai_init_lock:
        if not _vertexai_initialized:
            if vertexai is None:
                raise ImportError(
                    "vertexai is not installed. Install requirements.txt for live "
                    "inference, or enable demo mode."
                )
            project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
            if not project:
                raise OSError(
                    "GOOGLE_CLOUD_PROJECT environment variable is not set. "
                    "Copy .env.example to .env and fill in your project ID."
                )
            if not is_valid_project_id(project):
                raise ValueError(f"Invalid GCP project ID: {project!r}")
            logger.info("Initializing Vertex AI | project=%s | region=%s", project, _REGION)
            vertexai.init(project=project, location=_REGION)
            _vertexai_initialized = True


def _vertex_response_schema(model: type[BaseModel]) -> dict[str, object]:
    """Convert Pydantic JSON Schema into the subset accepted by Vertex AI."""
    schema = model.model_json_schema()
    defs = schema.get("$defs", {})

    def resolve(node: object) -> object:
        if isinstance(node, list):
            return [resolve(item) for item in node]
        if not isinstance(node, dict):
            return node

        if "$ref" in node:
            ref = node["$ref"]
            if ref.startswith("#/$defs/"):
                ref_name = ref.rsplit("/", 1)[-1]
                resolved = deepcopy(defs[ref_name])
                resolved.update({key: value for key, value in node.items() if key != "$ref"})
                return resolve(resolved)

        cleaned: dict[str, object] = {}
        prop_names: list[str] = []
        for key, value in node.items():
            if key == "properties":
                resolved_props = {
                    prop_name: resolve(prop_schema) for prop_name, prop_schema in value.items()
                }
                cleaned[key] = resolved_props
                prop_names = list(resolved_props)
            elif key in _VERTEX_SCHEMA_KEYS:
                cleaned[key] = resolve(value)
        if prop_names and "propertyOrdering" not in cleaned:
            cleaned["propertyOrdering"] = prop_names
        return cleaned

    resolved_schema = resolve(schema)
    if not isinstance(resolved_schema, dict):  # pragma: no cover - schema root is an object
        raise TypeError("Pydantic schema root must resolve to an object")
    return resolved_schema


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

    def __init__(self, project_id: str | None = None) -> None:
        _ensure_vertexai(project_id)
        self._model = GenerativeModel(
            _GEMINI_MODEL,
            system_instruction=self.instruction,
        )
        logger.info("Agent '%s' initialised with model %s", self.name, _GEMINI_MODEL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, image_bytes: bytes, context: dict[str, Any] | None = None) -> T:
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

        from ..telemetry import get_tracer

        with get_tracer().start_as_current_span(f"{self.name}.inference") as span:
            span.set_attribute("agent.name", self.name)
            span.set_attribute("agent.model", _GEMINI_MODEL)
            span.set_attribute("image.size_bytes", len(image_bytes))

            # Primary path: response_schema with Pydantic model
            try:
                response = self._model.generate_content(
                    [image_part, prompt],
                    generation_config=GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=_vertex_response_schema(self.output_model),
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

            span.set_attribute("output.status", result.__class__.__name__)

        logger.info("Agent '%s': completed → %s", self.name, result.__class__.__name__)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, context: dict[str, Any]) -> str:
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
        return self.output_model.model_validate_json(self._extract_json(response.text))

    @staticmethod
    def _extract_json(text: str) -> str:
        """Pull the JSON payload out of a model response.

        Handles responses wrapped in markdown fences (possibly with prose
        around them) without breaking on fences that appear mid-string.
        """
        text = text.strip()
        match = _JSON_FENCE_RE.search(text)
        if match:
            return match.group(1)
        return text

    @staticmethod
    def _detect_mime(data: bytes) -> str:
        """Detect the image MIME type from magic bytes."""
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:3] == b"GIF":
            return "image/gif"
        if data[:3] != b"\xff\xd8\xff":
            logger.warning("Unrecognized image magic bytes %r; defaulting to image/jpeg", data[:4])
        return "image/jpeg"
