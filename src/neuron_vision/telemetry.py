"""
Arize Phoenix telemetry for Neuron Vision Display.
Tracks all 5-agent QC pipeline calls with OpenTelemetry.
Partner track: Arize (Google Cloud Rapid Agent Hackathon)
"""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

try:
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
    _HAS_GOOGLE_GENAI_INSTR = True
except ImportError:
    _HAS_GOOGLE_GENAI_INSTR = False

try:
    from phoenix.otel import register as phoenix_register
    _HAS_PHOENIX = True
except ImportError:
    _HAS_PHOENIX = False


def setup_arize_tracing(project_name: str = "neuron-vision-display") -> trace.Tracer:
    """
    Configure Arize Phoenix OpenTelemetry tracing.

    Reads PHOENIX_API_KEY and PHOENIX_COLLECTOR_ENDPOINT from env.
    Falls back to local Phoenix if no endpoint configured.
    """
    if _HAS_PHOENIX:
        tracer_provider = phoenix_register(
            project_name=project_name,
            auto_instrument=True,
        )
        if _HAS_GOOGLE_GENAI_INSTR:
            GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    else:
        # Minimal fallback: standard OTLP provider
        tracer_provider = TracerProvider()
        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:4317")
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
            )
        except ImportError:
            pass
        trace.set_tracer_provider(tracer_provider)

    return trace.get_tracer(project_name)


_tracer: trace.Tracer | None = None


def get_tracer() -> trace.Tracer:
    """Return the global tracer (lazy init)."""
    global _tracer
    if _tracer is None:
        _tracer = setup_arize_tracing()
    return _tracer
