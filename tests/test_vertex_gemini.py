from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roboqc_agent.providers.vertex_gemini import VertexGeminiProvider


@dataclass
class FakeResponse:
    text: str = "ok"
    parsed: dict[str, str] | None = None


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        return FakeResponse()


class FakeClient:
    def __init__(self) -> None:
        self.models = FakeModels()


def test_generate_text_uses_configured_model() -> None:
    client = FakeClient()
    provider = VertexGeminiProvider(project="demo", client=client)

    result = provider.generate_text("inspect")

    assert result.text == "ok"
    assert client.models.calls[0]["model"] == "gemini-2.5-pro"
    assert client.models.calls[0]["contents"] == "inspect"
