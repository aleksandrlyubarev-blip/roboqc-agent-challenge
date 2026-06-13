"""Structured HTTP request logging for Cloud Run deployments."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, TypeAlias

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

logger = logging.getLogger("roboqc_agent.telemetry.request")

DEFAULT_SKIP_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/healthz",
        "/openapi.json",
        "/docs",
        "/redoc",
    }
)


@dataclass(frozen=True, slots=True)
class RequestLogRecord:
    """Normalized per-request record emitted to Cloud Logging."""

    method: str
    path: str
    status_code: int
    latency_ms: int
    request_id: str | None = None
    operator_id: str | None = None
    error: str | None = None

    def as_log_extra(self) -> dict[str, object]:
        """Return a structured logging payload."""

        return {
            "event": "http_request",
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "request_id": self.request_id,
            "operator_id": self.operator_id,
            "error": self.error,
        }


RequestLogSink: TypeAlias = Callable[[RequestLogRecord], None]


def log_request(record: RequestLogRecord) -> None:
    """Emit one structured request record."""

    logger.info("http_request", extra=record.as_log_extra())


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Log one structured record per non-probe HTTP request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        sink: RequestLogSink = log_request,
        skip_paths: frozenset[str] = DEFAULT_SKIP_PATHS,
    ) -> None:
        super().__init__(app)
        self._sink = sink
        self._skip_paths = skip_paths

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:
        if request.url.path in self._skip_paths:
            return await call_next(request)

        started = perf_counter()
        status_code = 500
        error: str | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:500]
            raise
        finally:
            self._emit(
                RequestLogRecord(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    latency_ms=int((perf_counter() - started) * 1000),
                    request_id=_request_id(request),
                    operator_id=_operator_id(request),
                    error=error,
                )
            )

    def _emit(self, record: RequestLogRecord) -> None:
        try:
            self._sink(record)
        except Exception:  # logging must never break requests
            logging.getLogger(__name__).debug("Request log sink failed", exc_info=True)


def _request_id(request: Request) -> str | None:
    state_id = getattr(request.state, "request_id", None)
    if state_id is not None:
        return str(state_id)
    header_id = request.headers.get("X-Request-Id")
    return header_id or None


def _operator_id(request: Request) -> str | None:
    operator_id = getattr(request.state, "operator_id", None)
    return str(operator_id) if operator_id is not None else None


__all__ = [
    "DEFAULT_SKIP_PATHS",
    "RequestLogMiddleware",
    "RequestLogRecord",
    "RequestLogSink",
    "log_request",
]
