from neuron_vision.telemetry import _build_otlp_headers


def test_build_otlp_headers_sets_project_name(monkeypatch) -> None:
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)

    assert _build_otlp_headers("neuron-vision-display") == {
        "x-project-name": "neuron-vision-display"
    }


def test_build_otlp_headers_sets_bearer_auth(monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")

    assert _build_otlp_headers("neuron-vision-display") == {
        "x-project-name": "neuron-vision-display",
        "authorization": "Bearer test-key",
    }


def test_build_otlp_headers_preserves_existing_bearer_prefix(monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_API_KEY", "Bearer test-key")

    assert _build_otlp_headers("neuron-vision-display")["authorization"] == "Bearer test-key"
