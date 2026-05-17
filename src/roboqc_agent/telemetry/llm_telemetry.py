"""Structured telemetry for Vertex Gemini calls."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

logger = logging.getLogger("roboqc_agent.telemetry.llm")

LLMEventKind: TypeAlias = Literal["llm_call", "llm_error"]
LLMOperation: TypeAlias = Literal["generate_text", "generate_multimodal"]


@dataclass(frozen=True, slots=True)
class LLMCallEvent:
    """Normalized per-call telemetry emitted by the Vertex provider."""

    event: LLMEventKind
    model: str
    operation: LLMOperation
    latency_ms: int
    request_id: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    error: str | None = None

    def as_log_extra(self) -> dict[str, object]:
        """Return a logging-compatible structured payload."""

        return {
            "event": self.event,
            "model": self.model,
            "operation": self.operation,
            "latency_ms": self.latency_ms,
            "request_id": self.request_id,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "error": self.error,
        }


TelemetrySink: TypeAlias = Callable[[LLMCallEvent], None]


def log_llm_event(event: LLMCallEvent) -> None:
    """Emit one structured log row per Gemini success or failure."""

    emit = logger.info if event.event == "llm_call" else logger.warning
    emit(event.event, extra=event.as_log_extra())


def build_success_event(
    *,
    model: str,
    operation: LLMOperation,
    latency_ms: int,
    response: Any,
) -> LLMCallEvent:
    """Normalize a successful SDK response into telemetry."""

    tokens_in, tokens_out = extract_usage_tokens(response)
    return LLMCallEvent(
        event="llm_call",
        model=model,
        operation=operation,
        latency_ms=latency_ms,
        request_id=extract_request_id(response),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )


def build_error_event(
    *,
    model: str,
    operation: LLMOperation,
    latency_ms: int,
    error: BaseException,
) -> LLMCallEvent:
    """Normalize a failed SDK call into telemetry."""

    return LLMCallEvent(
        event="llm_error",
        model=model,
        operation=operation,
        latency_ms=latency_ms,
        error=f"{type(error).__name__}: {error}"[:500],
    )


def extract_usage_tokens(response: Any) -> tuple[int | None, int | None]:
    """Extract prompt / candidate token counts from Google Gen AI responses."""

    usage = _read(response, "usage_metadata")
    if usage is None:
        return None, None
    return _coerce_optional_int(_read(usage, "prompt_token_count")), _coerce_optional_int(
        _read(usage, "candidates_token_count")
    )


def extract_request_id(response: Any) -> str | None:
    """Extract the most useful request identifier available on the response."""

    request_id = _read(response, "response_id")
    if request_id is None:
        request_id = _read(response, "id")
    return str(request_id) if request_id is not None else None


def _read(obj: Any, key: str) -> Any | None:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def _coerce_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "LLMCallEvent",
    "LLMEventKind",
    "LLMOperation",
    "TelemetrySink",
    "build_error_event",
    "build_success_event",
    "extract_request_id",
    "extract_usage_tokens",
    "log_llm_event",
]
