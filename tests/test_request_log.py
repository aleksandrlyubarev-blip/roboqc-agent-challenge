from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from roboqc_agent.telemetry.request_log import RequestLogMiddleware, RequestLogRecord


def _build_app(records: list[RequestLogRecord]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware, sink=records.append)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/inspect")
    async def inspect_tile(request: Request) -> dict[str, str]:
        request.state.operator_id = "operator-7"
        return {"status": "ok"}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("synthetic")

    return app


def test_request_log_records_non_probe_requests() -> None:
    records: list[RequestLogRecord] = []
    client = TestClient(_build_app(records))

    response = client.get("/inspect", headers={"X-Request-Id": "req-123"})

    assert response.status_code == 200
    assert records == [
        RequestLogRecord(
            method="GET",
            path="/inspect",
            status_code=200,
            latency_ms=records[0].latency_ms,
            request_id="req-123",
            operator_id="operator-7",
            error=None,
        )
    ]
    assert records[0].latency_ms >= 0


def test_request_log_skips_probe_paths() -> None:
    records: list[RequestLogRecord] = []
    client = TestClient(_build_app(records))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert records == []


def test_request_log_captures_500s() -> None:
    records: list[RequestLogRecord] = []
    client = TestClient(_build_app(records), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert len(records) == 1
    assert records[0].status_code == 500
    assert records[0].error == "RuntimeError: synthetic"


def test_request_log_sink_failure_does_not_break_response() -> None:
    def broken_sink(_: RequestLogRecord) -> None:
        raise RuntimeError("sink failed")

    app = FastAPI()
    app.add_middleware(RequestLogMiddleware, sink=broken_sink)

    @app.get("/inspect")
    async def inspect_tile() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)

    response = client.get("/inspect")

    assert response.status_code == 200
