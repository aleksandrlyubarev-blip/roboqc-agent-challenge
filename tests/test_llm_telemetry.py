from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from roboqc_agent.providers.vertex_gemini import VertexGeminiProvider
from roboqc_agent.telemetry.llm_telemetry import (
    LLMCallEvent,
    extract_request_id,
    extract_usage_tokens,
)


@dataclass
class FakeUsage:
    prompt_token_count: int = 17
    candidates_token_count: int = 9


@dataclass
class FakeResponse:
    text: str = "ok"
    parsed: dict[str, str] | None = None
    response_id: str = "resp-123"
    usage_metadata: FakeUsage | None = None


class FakeModels:
    def __init__(
        self,
        response: FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or FakeResponse(usage_metadata=FakeUsage())
        self.error = error

    def generate_content(self, **_: Any) -> FakeResponse:
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(
        self,
        response: FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.models = FakeModels(response=response, error=error)


def test_extract_usage_tokens_supports_google_response_shape() -> None:
    response = FakeResponse(usage_metadata=FakeUsage())

    assert extract_usage_tokens(response) == (17, 9)


def test_extract_request_id_prefers_response_id() -> None:
    response = FakeResponse(response_id="resp-123")

    assert extract_request_id(response) == "resp-123"


def test_provider_emits_success_telemetry() -> None:
    events: list[LLMCallEvent] = []
    provider = VertexGeminiProvider(
        project="demo",
        client=FakeClient(),
        telemetry_sink=events.append,
    )

    provider.generate_text("inspect")

    assert len(events) == 1
    event = events[0]
    assert event.event == "llm_call"
    assert event.model == "gemini-2.5-pro"
    assert event.operation == "generate_text"
    assert event.request_id == "resp-123"
    assert event.tokens_in == 17
    assert event.tokens_out == 9
    assert event.latency_ms >= 0


def test_provider_emits_error_telemetry() -> None:
    events: list[LLMCallEvent] = []
    provider = VertexGeminiProvider(
        project="demo",
        client=FakeClient(error=RuntimeError("boom")),
        telemetry_sink=events.append,
    )

    with pytest.raises(RuntimeError, match="boom"):
        provider.generate_text("inspect")

    assert len(events) == 1
    event = events[0]
    assert event.event == "llm_error"
    assert event.operation == "generate_text"
    assert event.error == "RuntimeError: boom"


def test_telemetry_sink_failure_does_not_break_generation() -> None:
    def broken_sink(_: LLMCallEvent) -> None:
        raise RuntimeError("sink failed")

    provider = VertexGeminiProvider(
        project="demo",
        client=FakeClient(),
        telemetry_sink=broken_sink,
    )

    result = provider.generate_text("inspect")

    assert result.text == "ok"
