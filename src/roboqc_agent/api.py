"""FastAPI surface for the RoboQC board-inspection workflow.

Wraps :class:`BoardFlowCoordinator` + the SQLite execution store in an HTTP
contract Cloud Run can serve:

* ``POST /boards`` — open a board run (expected tile count, lot, operator)
* ``POST /boards/{board_id}/tiles`` — record a finalized TileReport; the
  friction policy is enforced over the agent's proposed action
* ``POST /boards/{board_id}/operator-response`` — HITL: operator accepts or
  overrides a tile decision (required for tiles flagged ``triggered_hitl``)
* ``POST /boards/{board_id}/finalize`` — assemble and persist the QCReport
* ``GET /reports/{report_id}`` / ``GET /reports/{report_id}/timeline``
* ``GET /metrics`` — execution-store rollup

Auth note: the service relies on Cloud Run IAM (``--no-allow-unauthenticated``)
for caller identity; there is deliberately no in-app auth layer (see
``roboqc_agent.auth``).
"""

from __future__ import annotations

import threading
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from roboqc_agent.execution_store import SQLiteExecutionRepository
from roboqc_agent.orchestration.board_flow import BoardFlowCoordinator
from roboqc_agent.schemas import OperatorResponse, QCReport, TileReport
from roboqc_agent.telemetry import RequestLogMiddleware


class StartBoardRequest(BaseModel):
    """Open an inspection run for one board."""

    board_id: str = Field(min_length=1)
    lot_id: str = Field(min_length=1)
    operator_id: str = Field(min_length=1)
    expected_tiles: int = Field(gt=0)


class BoardProgress(BaseModel):
    """Progress snapshot returned by board mutations."""

    board_id: str
    tiles_recorded: int
    tiles_expected: int
    is_complete: bool
    pending_hitl_tile_ids: list[UUID]


class _BoardRegistry:
    """In-process registry of active board runs.

    Single-instance scope is acceptable here for the same reason the SQLite
    store is: one Cloud Run instance owns a board run end-to-end. Cross-
    instance coordination would need a shared store (Firestore/Cloud SQL).
    """

    def __init__(self, repository: SQLiteExecutionRepository) -> None:
        self._repository = repository
        self._boards: dict[str, BoardFlowCoordinator] = {}
        self._lock = threading.Lock()

    def start(self, request: StartBoardRequest) -> BoardFlowCoordinator:
        with self._lock:
            if request.board_id in self._boards:
                raise HTTPException(
                    status_code=409,
                    detail=f"Board {request.board_id!r} already has an active run",
                )
            coordinator = BoardFlowCoordinator(
                board_id=request.board_id,
                lot_id=request.lot_id,
                operator_id=request.operator_id,
                expected_tiles=request.expected_tiles,
                repository=self._repository,
            )
            self._boards[request.board_id] = coordinator
            return coordinator

    def get(self, board_id: str) -> BoardFlowCoordinator:
        with self._lock:
            coordinator = self._boards.get(board_id)
        if coordinator is None:
            raise HTTPException(status_code=404, detail=f"No active run for board {board_id!r}")
        return coordinator

    def close(self, board_id: str) -> None:
        with self._lock:
            self._boards.pop(board_id, None)


def _progress(coordinator: BoardFlowCoordinator) -> BoardProgress:
    return BoardProgress(
        board_id=coordinator.board_id,
        tiles_recorded=coordinator.tiles_recorded,
        tiles_expected=coordinator.expected_tiles,
        is_complete=coordinator.is_complete,
        pending_hitl_tile_ids=[tr.tile.tile_id for tr in coordinator.pending_hitl_tiles()],
    )


def create_app(repository: SQLiteExecutionRepository | None = None) -> FastAPI:
    """Create the RoboQC API app used by Cloud Run."""

    app = FastAPI(title="RoboQC Agent")
    app.add_middleware(RequestLogMiddleware)

    repo = repository or SQLiteExecutionRepository()
    registry = _BoardRegistry(repo)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "roboqc-agent"}

    @app.post("/boards", status_code=201, response_model=BoardProgress)
    async def start_board(request: StartBoardRequest) -> BoardProgress:
        return _progress(registry.start(request))

    @app.post("/boards/{board_id}/tiles", response_model=BoardProgress)
    async def record_tile(board_id: str, tile_report: TileReport) -> BoardProgress:
        coordinator = registry.get(board_id)
        try:
            coordinator.record_tile(tile_report)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _progress(coordinator)

    @app.post("/boards/{board_id}/operator-response", response_model=BoardProgress)
    async def record_operator_response(board_id: str, response: OperatorResponse) -> BoardProgress:
        coordinator = registry.get(board_id)
        try:
            coordinator.record_operator_response(response)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _progress(coordinator)

    @app.post("/boards/{board_id}/finalize", response_model=QCReport)
    async def finalize_board(board_id: str) -> QCReport:
        coordinator = registry.get(board_id)
        try:
            report = coordinator.finalize()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        registry.close(board_id)
        return report

    @app.get("/reports/{report_id}", response_model=QCReport)
    async def get_report(report_id: UUID) -> QCReport:
        report = repo.get_report(report_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        return report

    @app.get("/reports/{report_id}/timeline")
    async def get_timeline(report_id: UUID) -> list[dict[str, object]]:
        return [
            {
                "event": event.event,
                "payload": event.payload,
                "timestamp": event.timestamp,
            }
            for event in repo.get_timeline(report_id)
        ]

    @app.get("/metrics")
    async def metrics() -> dict[str, int]:
        return repo.metrics()

    return app


app = create_app()

__all__ = ["BoardProgress", "StartBoardRequest", "app", "create_app"]
