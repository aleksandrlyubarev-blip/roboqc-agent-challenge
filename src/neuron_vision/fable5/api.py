"""
FastAPI surface for the Fable 5 reasoning service (Cloud Run).

Endpoints:
    POST /analyze-defect    — full analysis (summary + root cause + recommendations)
    POST /root-cause        — causal analysis only
    POST /recommendations   — recommendations only
    GET  /healthz           — liveness (no model call, no secret access)

The Anthropic key is resolved once at startup (Secret Manager via Workload
Identity, env var for local dev) and the client is reused across requests.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from neuron_vision.fable5.client import Fable5Client, Fable5Config, Fable5Error
from neuron_vision.fable5.schemas import (
    DefectAnalysisRequest,
    DefectReasoningResponse,
    RecommendationsResponse,
    RootCauseResponse,
)
from neuron_vision.fable5.secrets import SecretResolutionError, resolve_anthropic_api_key

logger = logging.getLogger("neuron_vision.fable5.api")


def create_fable5_app(client: Fable5Client | None = None) -> FastAPI:
    """Create the reasoning service app; pass a client to skip secret lookup in tests."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if client is not None:
            app.state.fable5 = client
        else:
            try:
                api_key = resolve_anthropic_api_key()
            except SecretResolutionError:
                logger.exception("anthropic_key_unavailable")
                raise
            app.state.fable5 = Fable5Client(api_key=api_key, config=Fable5Config())
        try:
            yield
        finally:
            fable5: Fable5Client = app.state.fable5
            await fable5.aclose()

    app = FastAPI(
        title="Neuron Vision — Fable 5 Reasoning Service",
        version="1.0.0",
        lifespan=lifespan,
    )

    def _client() -> Fable5Client:
        fable5: Fable5Client = app.state.fable5
        return fable5

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "fable5-reasoning"}

    @app.post("/analyze-defect", response_model=DefectReasoningResponse)
    async def analyze_defect(payload: DefectAnalysisRequest) -> DefectReasoningResponse:
        try:
            return await _client().reason(payload)
        except Fable5Error as exc:
            # Both primary and fallback failed — surface as 503 so the
            # dashboard can degrade gracefully instead of retrying blindly.
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/root-cause", response_model=RootCauseResponse)
    async def root_cause(payload: DefectAnalysisRequest) -> RootCauseResponse:
        try:
            return await _client().analyze_root_cause(payload)
        except Fable5Error as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/recommendations", response_model=RecommendationsResponse)
    async def recommendations(payload: DefectAnalysisRequest) -> RecommendationsResponse:
        try:
            return await _client().generate_recommendations(payload)
        except Fable5Error as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return app


app = create_fable5_app()

__all__ = ["app", "create_fable5_app"]
