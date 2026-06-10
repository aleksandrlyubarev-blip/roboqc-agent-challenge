"""
Smoke test for Arize Phoenix / OpenInference telemetry bootstrap.

Verifies that ``init_tracer`` can be imported and invoked against an offline
endpoint without crashing, and that it degrades gracefully when the optional
OpenInference / Phoenix dependencies are not installed. No live Phoenix or
Vertex AI connection is required — the OTLP exporter is lazy/batched, so no
network call happens during initialization.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Mirror app.py's import style: ``from src.neuron_vision.telemetry import ...``.
# Ensure the repo root is importable regardless of how pytest resolves paths.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.neuron_vision.telemetry import init_tracer  # noqa: E402


def test_init_tracer_offline_does_not_crash(monkeypatch) -> None:
    """init_tracer must return a usable tracer against an offline endpoint."""
    # Never launch a local Phoenix UI or pretend to be on Cloud Run.
    monkeypatch.setenv("PHOENIX_LAUNCH_LOCAL", "0")
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)

    tracer = init_tracer(
        project_name="neuron-vision-display-test",
        phoenix_endpoint="http://localhost:6006/v1/traces",
    )

    assert tracer is not None
    # The returned tracer must be able to open a span without raising.
    with tracer.start_as_current_span("smoke-test-span") as span:
        assert span is not None


def test_init_tracer_is_idempotent(monkeypatch) -> None:
    """Repeated calls return the cached tracer rather than reinitializing."""
    monkeypatch.setenv("PHOENIX_LAUNCH_LOCAL", "0")
    monkeypatch.delenv("K_SERVICE", raising=False)

    first = init_tracer(phoenix_endpoint="http://localhost:6006/v1/traces")
    second = init_tracer(phoenix_endpoint="http://localhost:6006/v1/traces")

    assert first is second


def test_init_tracer_importable_from_package() -> None:
    """The package should re-export init_tracer for `from neuron_vision import ...`."""
    import src.neuron_vision as nv

    assert nv.init_tracer is not None
    assert nv.get_tracer is not None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
