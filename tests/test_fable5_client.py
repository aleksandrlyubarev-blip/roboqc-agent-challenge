"""Offline unit tests for the Fable 5 integration (no network, no real SDK calls)."""

from __future__ import annotations

from typing import Any

import pytest

from neuron_vision.fable5.cache import TTLCache
from neuron_vision.fable5.client import Fable5Client, Fable5Config, sanitize_json_schema
from neuron_vision.fable5.schemas import (
    DefectAnalysisRequest,
    DefectObservation,
    DefectReasoning,
)
from neuron_vision.fable5.telemetry import estimate_cost_usd

# ---------------------------------------------------------------------------
# Schema sanitizer
# ---------------------------------------------------------------------------


def test_sanitize_strips_numeric_constraints_and_locks_objects() -> None:
    schema = DefectReasoning.model_json_schema()
    cleaned = sanitize_json_schema(schema)

    def assert_clean(node: Any) -> None:
        if isinstance(node, dict):
            assert "minimum" not in node and "maximum" not in node
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
            for value in node.values():
                assert_clean(value)
        elif isinstance(node, list):
            for item in node:
                assert_clean(item)

    assert_clean(cleaned)
    # The original schema (with ge/le on confidence) is left untouched.
    assert "maximum" in str(schema)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def test_estimate_cost_matches_published_pricing() -> None:
    # Fable 5: $10 input / $50 output per MTok.
    assert estimate_cost_usd("claude-fable-5", 1_000_000, 0) == pytest.approx(10.0)
    assert estimate_cost_usd("claude-fable-5", 0, 1_000_000) == pytest.approx(50.0)
    # Opus 4.8 fallback is half the price.
    assert estimate_cost_usd("claude-opus-4-8", 1_000_000, 1_000_000) == pytest.approx(30.0)
    assert estimate_cost_usd("unknown-model", 1000, 1000) == 0.0


# ---------------------------------------------------------------------------
# TTL cache
# ---------------------------------------------------------------------------


def test_cache_roundtrip_and_eviction() -> None:
    cache = TTLCache(max_entries=2, ttl_seconds=60)
    k1 = TTLCache.fingerprint("reason", {"prompt": "a"})
    k2 = TTLCache.fingerprint("reason", {"prompt": "b"})
    k3 = TTLCache.fingerprint("reason", {"prompt": "c"})
    assert k1 != k2

    cache.put(k1, "v1")
    cache.put(k2, "v2")
    assert cache.get(k1) == "v1"
    cache.put(k3, "v3")  # evicts k2 (k1 was touched more recently)
    assert cache.get(k2) is None
    assert cache.get(k1) == "v1"
    assert cache.get(k3) == "v3"


def test_cache_expiry() -> None:
    cache = TTLCache(max_entries=4, ttl_seconds=0.0)
    key = TTLCache.fingerprint("reason", {"prompt": "x"})
    cache.put(key, "v")
    assert cache.get(key) is None


# ---------------------------------------------------------------------------
# Client: refusal fallback + cache integration (stubbed SDK)
# ---------------------------------------------------------------------------

_REASONING_JSON = DefectReasoning(
    summary="Mura caused by uneven cell-gap after ODF process drift.",
    root_cause={
        "primary_root_cause": "ODF dispenser drift",
        "causal_chain": ["dispenser drift", "uneven cell gap", "mura"],
        "contributing_factors": [],
        "ruled_out": ["backlight defect: pattern moves with panel"],
        "confidence": 0.8,
    },
    recommendations=[],
).model_dump_json()


class _Usage:
    input_tokens = 1200
    output_tokens = 340


class _TextBlock:
    type = "text"
    text = _REASONING_JSON


class _Response:
    def __init__(self, stop_reason: str) -> None:
        self.stop_reason = stop_reason
        self.content = [_TextBlock()]
        self.usage = _Usage()


class _StubMessages:
    def __init__(self, refuse_models: set[str]) -> None:
        self.refuse_models = refuse_models
        self.calls: list[str] = []

    async def create(self, **kwargs: Any) -> _Response:
        model = kwargs["model"]
        self.calls.append(model)
        if model in self.refuse_models:
            return _Response(stop_reason="refusal")
        return _Response(stop_reason="end_turn")


class _StubAnthropicClient:
    def __init__(self, refuse_models: set[str]) -> None:
        self.messages = _StubMessages(refuse_models)

    async def close(self) -> None:  # pragma: no cover - interface parity
        return None


def _request() -> DefectAnalysisRequest:
    return DefectAnalysisRequest(
        defects=[
            DefectObservation(
                defect_type="mura",
                location="center",
                severity="moderate",
                confidence=0.9,
            )
        ]
    )


@pytest.mark.asyncio
async def test_reason_happy_path_uses_primary_model() -> None:
    stub = _StubAnthropicClient(refuse_models=set())
    client = Fable5Client(api_key="test", client=stub)  # type: ignore[arg-type]

    response = await client.reason(_request())

    assert stub.messages.calls == ["claude-fable-5"]
    assert response.meta.model_id == "claude-fable-5"
    assert response.meta.fallback_used is False
    assert response.meta.estimated_cost_usd > 0
    assert response.result.root_cause.primary_root_cause == "ODF dispenser drift"


@pytest.mark.asyncio
async def test_refusal_falls_back_to_opus() -> None:
    stub = _StubAnthropicClient(refuse_models={"claude-fable-5"})
    client = Fable5Client(api_key="test", client=stub)  # type: ignore[arg-type]

    response = await client.reason(_request())

    assert stub.messages.calls == ["claude-fable-5", "claude-opus-4-8"]
    assert response.meta.model_id == "claude-opus-4-8"
    assert response.meta.fallback_used is True
    assert "refusal" in response.meta.fallback_reason


@pytest.mark.asyncio
async def test_repeat_request_is_served_from_cache() -> None:
    stub = _StubAnthropicClient(refuse_models=set())
    client = Fable5Client(
        api_key="test",
        config=Fable5Config(cache_ttl_seconds=60),
        client=stub,  # type: ignore[arg-type]
    )

    first = await client.reason(_request())
    second = await client.reason(_request())

    assert stub.messages.calls == ["claude-fable-5"]  # one real call only
    assert first.meta.cached is False
    assert second.meta.cached is True
    assert second.result == first.result
