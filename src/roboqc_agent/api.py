"""Minimal FastAPI surface for Cloud Run health and future graph endpoints."""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create the RoboQC API app used by Cloud Run."""

    app = FastAPI(title="RoboQC Agent")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "roboqc-agent"}

    return app


app = create_app()

__all__ = ["app", "create_app"]
