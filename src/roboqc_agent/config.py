"""Central runtime configuration for RoboQC agents and providers.

Values resolve from environment variables at call time (not import time) so
tests and Cloud Run revisions can override them without re-importing modules.
"""

from __future__ import annotations

import os

FALLBACK_MODEL = "gemini-2.5-pro"
FALLBACK_LOCATION = "us-central1"

MODEL_ENV_VAR = "ROBOQC_MODEL"
LOCATION_ENV_VAR = "GOOGLE_CLOUD_LOCATION"


def default_model() -> str:
    """Gemini model used by all RoboQC agents unless explicitly overridden."""

    return os.getenv(MODEL_ENV_VAR) or FALLBACK_MODEL


def default_location() -> str:
    """Vertex AI region for provider clients."""

    return os.getenv(LOCATION_ENV_VAR) or FALLBACK_LOCATION


__all__ = [
    "FALLBACK_LOCATION",
    "FALLBACK_MODEL",
    "LOCATION_ENV_VAR",
    "MODEL_ENV_VAR",
    "default_location",
    "default_model",
]
