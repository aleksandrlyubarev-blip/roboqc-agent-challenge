"""
Neuron Vision Display — multi-agent visual QC system for SMT PCB manufacturing.
System: RomeoFlexVision | Stack: Google ADK + Vertex AI Gemini 2.5 Pro + Pydantic v2
"""
__version__ = "1.0.0"
__system__ = "RomeoFlexVision"
__product__ = "Neuron Vision Display"

# Arize Phoenix / OpenInference tracing entry points.
# Imported lazily-safe: telemetry depends on opentelemetry, which is a declared
# dependency but optional at import time, so degrade gracefully if it is absent.
try:
    from .telemetry import get_tracer, init_tracer
except Exception:  # pragma: no cover - tracing deps optional in some envs
    init_tracer = None  # type: ignore[assignment]
    get_tracer = None  # type: ignore[assignment]

__all__ = [
    "__version__",
    "__system__",
    "__product__",
    "init_tracer",
    "get_tracer",
]
