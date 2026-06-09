"""
Arize Phoenix / OpenInference tracing for Neuron Vision Display.

The live pipeline uses the Vertex AI SDK:
    from vertexai.generative_models import GenerativeModel

Therefore the correct OpenInference instrumentor is
``openinference-instrumentation-vertexai``. The google-genai instrumentor does
not patch these calls.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_PROJECT_NAME = "neuron-vision-display"
_LOCAL_PHOENIX_ENDPOINT = "http://localhost:6006/v1/traces"

_tracer: trace.Tracer | None = None
_initialized = False


def init_tracer(
    project_name: str = _PROJECT_NAME,
    phoenix_endpoint: str | None = None,
) -> trace.Tracer:
    """
    Initialize tracing once and return the project tracer.

    Cloud Run must set ``PHOENIX_COLLECTOR_ENDPOINT`` to a hosted Phoenix or
    Arize endpoint. Local development falls back to ``localhost:6006`` and tries
    to launch a Phoenix UI if Phoenix is installed.
    """
    global _initialized, _tracer

    if _initialized and _tracer is not None:
        return _tracer

    endpoint = (
        phoenix_endpoint
        or os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
        or _LOCAL_PHOENIX_ENDPOINT
    )
    running_on_cloud_run = bool(os.getenv("K_SERVICE"))

    provider = TracerProvider()

    if running_on_cloud_run and endpoint.startswith("http://localhost"):
        logger.warning(
            "PHOENIX_COLLECTOR_ENDPOINT is not set on Cloud Run; "
            "OpenInference spans will be created but not exported."
        )
    else:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        except ImportError as exc:
            logger.warning("OTLP HTTP exporter unavailable; tracing export disabled: %s", exc)

    trace.set_tracer_provider(provider)

    if not running_on_cloud_run and os.getenv("PHOENIX_LAUNCH_LOCAL", "1") != "0":
        try:
            import phoenix as px

            session = px.launch_app()
            logger.info("Arize Phoenix UI available at %s", session.url)
        except Exception as exc:  # Phoenix UI is optional for local runs.
            logger.info("Local Phoenix UI was not launched: %s", exc)

    try:
        from openinference.instrumentation.vertexai import VertexAIInstrumentor

        _instrument_vertexai(VertexAIInstrumentor(), provider)
        logger.info("Vertex AI OpenInference instrumentation enabled")
    except ImportError as exc:
        logger.warning(
            "openinference-instrumentation-vertexai is not installed; "
            "Gemini auto-instrumentation disabled: %s",
            exc,
        )
    except Exception as exc:
        logger.warning("Vertex AI OpenInference instrumentation failed: %s", exc)

    _tracer = trace.get_tracer(project_name)
    _initialized = True
    logger.info(
        "Arize Phoenix tracing initialized | project=%s | endpoint=%s",
        project_name,
        endpoint,
    )
    return _tracer


def get_tracer() -> trace.Tracer:
    """Return the global tracer, initializing telemetry lazily if needed."""
    return init_tracer()


def _instrument_vertexai(instrumentor: Any, provider: TracerProvider) -> None:
    """Support OpenInference versions with and without tracer_provider argument."""
    try:
        instrumentor.instrument(tracer_provider=provider)
    except TypeError:
        instrumentor.instrument()
