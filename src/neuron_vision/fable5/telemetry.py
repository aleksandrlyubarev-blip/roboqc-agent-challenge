"""
Structured telemetry for Claude Fable 5 calls.

One JSON log row per call (success, fallback or error) — Cloud Logging picks
these up from stdout on Cloud Run. We log metadata only (model, tokens,
latency, cost, error type), never prompt or response bodies, because defect
data may reference customer products.

Cost tracking matters here: Fable 5 ($10/$50 per MTok) is twice the price of
Opus 4.8 ($5/$25), so per-call cost estimates feed the spend dashboard
(see infra/monitoring).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, TypeAlias

logger = logging.getLogger("neuron_vision.fable5.llm")

Fable5EventKind: TypeAlias = Literal["fable5_call", "fable5_fallback", "fable5_error"]

# USD per 1M tokens (input, output). Update alongside model upgrades.
MODEL_PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
}


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate one call's cost in USD; 0.0 for unknown models."""

    pricing = MODEL_PRICING_USD_PER_MTOK.get(model_id)
    if pricing is None:
        return 0.0
    input_rate, output_rate = pricing
    return round((input_tokens * input_rate + output_tokens * output_rate) / 1_000_000, 6)


@dataclass(frozen=True, slots=True)
class Fable5CallEvent:
    """Normalized per-call telemetry for the Fable 5 client."""

    event: Fable5EventKind
    model: str
    operation: str
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    fallback_from: str | None = None
    fallback_reason: str | None = None
    error_type: str | None = None
    request_id: str | None = None

    def as_log_extra(self) -> dict[str, object]:
        """Return a logging-compatible structured payload."""

        return {
            "event": self.event,
            "model": self.model,
            "operation": self.operation,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "fallback_from": self.fallback_from,
            "fallback_reason": self.fallback_reason,
            "error_type": self.error_type,
            "request_id": self.request_id,
        }


def log_fable5_event(event: Fable5CallEvent) -> None:
    """Emit one structured log row per Fable 5 call outcome."""

    emit = logger.info if event.event == "fable5_call" else logger.warning
    emit(event.event, extra=event.as_log_extra())
