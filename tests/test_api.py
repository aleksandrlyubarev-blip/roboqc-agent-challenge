from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from roboqc_agent.api import create_app
from roboqc_agent.schemas import (
    Action,
    ActionKind,
    BBox,
    Defect,
    DefectClass,
    FMEAEntry,
    OperatorAction,
    OperatorResponse,
    Severity,
    Tile,
    TilePosition,
    TileReport,
)


def test_healthz_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "roboqc-agent"}


def _tile_report(board_id: str, *, hitl: bool = False) -> TileReport:
    tile = Tile(
        board_id=board_id,
        lot_id="lot-1",
        position=TilePosition(row=0, col=0),
        magnification=10,
        image_uri="gs://demo/tile.png",
        captured_at=datetime.now(UTC),
        operator_id="op-1",
    )
    if hitl:
        # Low confidence routes to human review via the friction policy.
        defect = Defect(
            tile_id=tile.tile_id,
            defect_class=DefectClass.OPEN_TRACE,
            bbox=BBox(x=1, y=1, w=2, h=2),
            confidence=0.5,
            source="labeled_detector",
        )
        defects = [defect]
        entries = [
            FMEAEntry(
                defect_id=defect.defect_id,
                severity=Severity.MAJOR,
                default_action=ActionKind.REWORK,
                justification="low confidence open trace",
            )
        ]
        kind = ActionKind.HUMAN_REVIEW
    else:
        defects = []
        entries = []
        kind = ActionKind.PASS
    return TileReport(
        tile=tile,
        defects=defects,
        fmea_entries=entries,
        agent_action=Action(
            tile_id=tile.tile_id,
            kind=kind,
            reason="agent proposal",
            triggered_hitl=hitl,
            confidence=0.5 if hitl else 1.0,
        ),
    )


def _post_json(client: TestClient, url: str, model: Any) -> Any:
    return client.post(
        url,
        content=model.model_dump_json().encode(),
        headers={"Content-Type": "application/json"},
    )


def test_board_lifecycle_pass() -> None:
    client = TestClient(create_app())

    started = client.post(
        "/boards",
        json={
            "board_id": "board-1",
            "lot_id": "lot-1",
            "operator_id": "op-1",
            "expected_tiles": 2,
        },
    )
    assert started.status_code == 201
    assert started.json()["tiles_recorded"] == 0

    first = _post_json(client, "/boards/board-1/tiles", _tile_report("board-1"))
    assert first.status_code == 200
    assert first.json()["is_complete"] is False

    early = client.post("/boards/board-1/finalize")
    assert early.status_code == 409

    second = _post_json(client, "/boards/board-1/tiles", _tile_report("board-1"))
    assert second.json()["is_complete"] is True

    finalized = client.post("/boards/board-1/finalize")
    assert finalized.status_code == 200
    report = finalized.json()
    assert report["status"] == "pass"
    assert len(report["tile_reports"]) == 2

    fetched = client.get(f"/reports/{report['report_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["board_id"] == "board-1"

    timeline = client.get(f"/reports/{report['report_id']}/timeline")
    assert [event["event"] for event in timeline.json()] == [
        "tile_finalized",
        "tile_finalized",
        "board_finalized",
    ]

    metrics = client.get("/metrics")
    assert metrics.json()["completed_reports"] == 1

    # The run is closed: the board can be inspected again later.
    assert client.post("/boards/board-1/finalize").status_code == 404


def test_hitl_gate_blocks_finalization_until_operator_decides() -> None:
    client = TestClient(create_app())
    client.post(
        "/boards",
        json={
            "board_id": "board-2",
            "lot_id": "lot-1",
            "operator_id": "op-1",
            "expected_tiles": 1,
        },
    )
    tile_report = _tile_report("board-2", hitl=True)
    recorded = _post_json(client, "/boards/board-2/tiles", tile_report)
    assert recorded.json()["pending_hitl_tile_ids"] == [str(tile_report.tile.tile_id)]

    blocked = client.post("/boards/board-2/finalize")
    assert blocked.status_code == 409
    assert "operator decision pending" in blocked.json()["detail"]

    override = OperatorResponse(
        tile_id=tile_report.tile.tile_id,
        operator_id="op-1",
        action=OperatorAction.OVERRIDE,
        final_kind=ActionKind.PASS,
        rationale="False positive: shadow artifact, verified under microscope.",
        responded_at=datetime.now(UTC),
    )
    responded = _post_json(client, "/boards/board-2/operator-response", override)
    assert responded.status_code == 200
    assert responded.json()["pending_hitl_tile_ids"] == []

    finalized = client.post("/boards/board-2/finalize")
    assert finalized.status_code == 200
    report = finalized.json()
    # Operator override wins over the agent's HUMAN_REVIEW proposal.
    assert report["status"] == "pass"
    assert report["operator_signoff_at"] is not None
    assert report["senior_escalations"] == [str(tile_report.tile.tile_id)]


def test_operator_response_for_unknown_tile_is_404() -> None:
    client = TestClient(create_app())
    client.post(
        "/boards",
        json={
            "board_id": "board-3",
            "lot_id": "lot-1",
            "operator_id": "op-1",
            "expected_tiles": 1,
        },
    )
    orphan = OperatorResponse(
        tile_id=uuid4(),
        operator_id="op-1",
        action=OperatorAction.ACCEPT,
        final_kind=ActionKind.PASS,
        responded_at=datetime.now(UTC),
    )
    assert _post_json(client, "/boards/board-3/operator-response", orphan).status_code == 404


def test_duplicate_board_run_is_409() -> None:
    client = TestClient(create_app())
    body = {
        "board_id": "board-4",
        "lot_id": "lot-1",
        "operator_id": "op-1",
        "expected_tiles": 1,
    }
    assert client.post("/boards", json=body).status_code == 201
    assert client.post("/boards", json=body).status_code == 409


def test_tile_for_unknown_board_is_404() -> None:
    client = TestClient(create_app())
    response = _post_json(client, "/boards/ghost/tiles", _tile_report("ghost"))
    assert response.status_code == 404
