"""Vertex AI Gemini provider for RoboQC multimodal generation."""

from __future__ import annotations

import mimetypes
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from roboqc_agent.telemetry import (
    LLMOperation,
    TelemetrySink,
    build_error_event,
    build_success_event,
    log_llm_event,
)

if TYPE_CHECKING:
    from google.genai import types as genai_types


@dataclass(slots=True)
class GenerationResult:
    """Normalized result returned by the provider."""

    text: str | None
    parsed: Any | None
    raw: Any


class VertexGeminiProvider:
    """Thin wrapper around the Google Gen AI SDK configured for Vertex AI."""

    def __init__(
        self,
        *,
        project: str,
        location: str = "us-central1",
        model: str = "gemini-2.5-pro",
        client: Any | None = None,
        telemetry_sink: TelemetrySink = log_llm_event,
    ) -> None:
        self.project = project
        self.location = location
        self.model = model
        self.client = client or self._build_default_client(project=project, location=location)
        self.telemetry_sink = telemetry_sink

    def generate_text(
        self,
        prompt: str,
        *,
        response_schema: type[BaseModel] | dict[str, Any] | None = None,
    ) -> GenerationResult:
        return self._generate(
            operation="generate_text",
            contents=prompt,
            response_schema=response_schema,
        )

    def generate_multimodal(
        self,
        images: Sequence[str | Path],
        prompt: str,
        *,
        response_schema: type[BaseModel] | dict[str, Any] | None = None,
    ) -> GenerationResult:
        contents: list[Any] = [prompt]
        contents.extend(self._part_from_image_path(Path(image)) for image in images)
        return self._generate(
            operation="generate_multimodal",
            contents=contents,
            response_schema=response_schema,
        )

    def _generate(
        self,
        *,
        operation: LLMOperation,
        contents: Any,
        response_schema: type[BaseModel] | dict[str, Any] | None,
    ) -> GenerationResult:
        started = perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=self._build_config(response_schema=response_schema),
            )
        except Exception as exc:
            self._emit_telemetry(
                build_error_event(
                    model=self.model,
                    operation=operation,
                    latency_ms=self._latency_ms(started),
                    error=exc,
                )
            )
            raise

        self._emit_telemetry(
            build_success_event(
                model=self.model,
                operation=operation,
                latency_ms=self._latency_ms(started),
                response=response,
            )
        )
        return self._normalize_response(response)

    @staticmethod
    def _latency_ms(started: float) -> int:
        return int((perf_counter() - started) * 1000)

    def _emit_telemetry(self, event: Any) -> None:
        try:
            self.telemetry_sink(event)
        except Exception:  # pragma: no cover - telemetry must not break inference
            pass

    @staticmethod
    def _build_default_client(*, project: str, location: str) -> Any:
        from google import genai
        from google.genai import types

        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options=types.HttpOptions(api_version="v1"),
        )

    @staticmethod
    def _build_config(
        *,
        response_schema: type[BaseModel] | dict[str, Any] | None,
    ) -> Any | None:
        if response_schema is None:
            return None

        from google.genai import types

        return types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )

    @staticmethod
    def _part_from_image_path(path: Path) -> genai_types.Part:
        from google.genai import types

        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type is None:
            raise ValueError(f"Unable to infer MIME type for image: {path}")
        return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type)

    @staticmethod
    def _normalize_response(response: Any) -> GenerationResult:
        return GenerationResult(
            text=getattr(response, "text", None),
            parsed=getattr(response, "parsed", None),
            raw=response,
        )
