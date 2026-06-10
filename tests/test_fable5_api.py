"""Offline tests for the Fable 5 FastAPI surface (stubbed Anthropic SDK)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from neuron_vision.fable5.api import create_fable5_app
from neuron_vision.fable5.client import Fable5Client
from neuron_vision.fable5.schemas import DefectReasoning, RecommendationSet, RootCauseAnalysis

_SAMPLE_REQUEST = json.loads(
    (Path(__file__).parent.parent / "data" / "fable5_sample_request.json").read_text()
)

_ROOT_CAUSE = RootCauseAnalysis(
    primary_root_cause="ACF lot change on line A",
    causal_chain=["new ACF lot", "marginal bonding adhesion", "open gate line", "line defect"],
    contributing_factors=[],
    ruled_out=["panel input board: defect persists with known-good board"],
    confidence=0.78,
)
_REASONING_JSON = DefectReasoning(
    summary="Line-defect spike correlates with the new ACF lot installed on line A.",
    root_cause=_ROOT_CAUSE,
    recommendations=[],
).model_dump_json()
_ROOT_CAUSE_JSON = _ROOT_CAUSE.model_dump_json()
_RECOMMENDATIONS_JSON = RecommendationSet(
    recommendations=[],
    quick_wins=["quarantine ACF lot 2026-06-08", "re-bond one panel with previous lot"],
    summary="Quarantine the suspect ACF lot and verify with a controlled re-bond.",
).model_dump_json()

_PAYLOAD_BY_OPERATION = {
    "full analysis": _REASONING_JSON,
    "root cause analysis only": _ROOT_CAUSE_JSON,
    "actionable recommendations for the line": _RECOMMENDATIONS_JSON,
}


class _Usage:
    input_tokens = 900
    output_tokens = 250


class _TextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.stop_reason = stop_reason
        self.content = [_TextBlock(text)]
        self.usage = _Usage()


class _StubMessages:
    def __init__(self, fail: bool) -> None:
        self.fail = fail

    async def create(self, **kwargs: Any) -> _Response:
        if self.fail:
            import anthropic

            raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://test"))
        prompt: str = kwargs["messages"][0]["content"]
        for marker, payload in _PAYLOAD_BY_OPERATION.items():
            if f"Requested output: {marker}." in prompt:
                return _Response(payload)
        raise AssertionError(f"Unexpected prompt: {prompt[:80]}")


class _StubAnthropicClient:
    def __init__(self, fail: bool = False) -> None:
        self.messages = _StubMessages(fail)

    async def close(self) -> None:  # pragma: no cover - interface parity
        return None


def _app_client(fail: bool = False) -> TestClient:
    fable5 = Fable5Client(api_key="test", client=_StubAnthropicClient(fail))  # type: ignore[arg-type]
    return TestClient(create_fable5_app(client=fable5))


def test_healthz() -> None:
    with _app_client() as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_defect_returns_envelope_with_meta() -> None:
    with _app_client() as client:
        response = client.post("/analyze-defect", json=_SAMPLE_REQUEST)
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["root_cause"]["primary_root_cause"] == "ACF lot change on line A"
    assert body["meta"]["model_id"] == "claude-fable-5"
    assert body["meta"]["fallback_used"] is False
    assert body["meta"]["estimated_cost_usd"] > 0


def test_root_cause_and_recommendations_endpoints() -> None:
    with _app_client() as client:
        rc = client.post("/root-cause", json=_SAMPLE_REQUEST)
        recs = client.post("/recommendations", json=_SAMPLE_REQUEST)
    assert rc.status_code == 200
    assert rc.json()["result"]["confidence"] == 0.78
    assert recs.status_code == 200
    assert "ACF" in recs.json()["result"]["quick_wins"][0]


def test_validation_error_returns_422() -> None:
    with _app_client() as client:
        response = client.post("/analyze-defect", json={"defects": []})
    assert response.status_code == 422


def test_total_failure_returns_503() -> None:
    # Both Fable 5 and the Opus 4.8 fallback fail at transport level.
    with _app_client(fail=True) as client:
        response = client.post("/analyze-defect", json=_SAMPLE_REQUEST)
    assert response.status_code == 503
    assert "claude-fable-5" in response.json()["detail"]
