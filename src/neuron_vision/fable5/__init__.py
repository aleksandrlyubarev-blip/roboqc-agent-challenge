"""
Claude Fable 5 integration for Neuron Vision Display (RomeoFlexVision).

Production path: Cloud Run service (``neuron_vision.fable5.api``) calling the
Anthropic Messages API through :class:`Fable5Client`, with the API key sourced
from Google Cloud Secret Manager and graceful fallback to Claude Opus 4.8.
"""

from __future__ import annotations

from neuron_vision.fable5.client import Fable5Client, Fable5Config, Fable5Error
from neuron_vision.fable5.schemas import (
    DefectAnalysisRequest,
    DefectObservation,
    DefectReasoning,
    Fable5CallMeta,
    ProcessContext,
    RecommendationSet,
    RootCauseAnalysis,
)

__all__ = [
    "DefectAnalysisRequest",
    "DefectObservation",
    "DefectReasoning",
    "Fable5CallMeta",
    "Fable5Client",
    "Fable5Config",
    "Fable5Error",
    "ProcessContext",
    "RecommendationSet",
    "RootCauseAnalysis",
]
