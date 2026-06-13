from __future__ import annotations

from datetime import UTC, datetime

from roboqc_agent.schemas import (
    Action,
    ActionKind,
    BBox,
    Defect,
    DefectClass,
    Tile,
    TilePosition,
)


def test_tile_and_defect_contracts_round_trip() -> None:
    tile = Tile(
        board_id="board-1",
        lot_id="lot-1",
        position=TilePosition(row=2, col=3),
        magnification=10,
        image_uri="gs://demo/tile.png",
        captured_at=datetime.now(UTC),
        operator_id="op-1",
    )
    defect = Defect(
        tile_id=tile.tile_id,
        defect_class=DefectClass.OPEN_TRACE,
        bbox=BBox(x=1, y=2, w=3, h=4),
        confidence=0.91,
        source="labeled_detector",
    )
    action = Action(
        tile_id=tile.tile_id,
        kind=ActionKind.HUMAN_REVIEW,
        reason="low confidence",
        triggered_hitl=True,
        confidence=defect.confidence,
    )

    assert defect.tile_id == tile.tile_id
    assert action.kind is ActionKind.HUMAN_REVIEW


def _make_tile() -> Tile:
    return Tile(
        board_id="board-1",
        lot_id="lot-1",
        position=TilePosition(row=0, col=0),
        magnification=10,
        image_uri="gs://demo/tile.png",
        captured_at=datetime.now(UTC),
        operator_id="op-1",
    )


def test_tile_rejects_non_gcs_image_uri() -> None:
    import pytest

    with pytest.raises(ValueError, match="gs://"):
        Tile(
            board_id="board-1",
            lot_id="lot-1",
            position=TilePosition(row=0, col=0),
            magnification=10,
            image_uri="https://example.com/tile.png",
            captured_at=datetime.now(UTC),
            operator_id="op-1",
        )


def test_action_reason_is_length_bounded() -> None:
    import pytest

    from roboqc_agent.schemas import MAX_RATIONALE_LENGTH

    with pytest.raises(ValueError):
        Action(
            tile_id=_make_tile().tile_id,
            kind=ActionKind.PASS,
            reason="x" * (MAX_RATIONALE_LENGTH + 1),
            confidence=0.9,
        )


def test_operator_response_requires_rationale_on_override() -> None:
    import pytest

    from roboqc_agent.schemas import OperatorAction, OperatorResponse

    with pytest.raises(ValueError, match="rationale"):
        OperatorResponse(
            tile_id=_make_tile().tile_id,
            operator_id="op-1",
            action=OperatorAction.OVERRIDE,
            final_kind=ActionKind.PASS,
            responded_at=datetime.now(UTC),
        )


def test_qc_report_fills_and_enforces_histogram() -> None:
    import pytest

    from roboqc_agent.schemas import BoardStatus, QCReport, TileReport

    tile = _make_tile()
    defect = Defect(
        tile_id=tile.tile_id,
        defect_class=DefectClass.PINHOLE,
        bbox=BBox(x=1, y=1, w=2, h=2),
        confidence=0.9,
        source="anomaly_arm",
    )
    tile_report = TileReport(
        tile=tile,
        defects=[defect],
        fmea_entries=[],
        agent_action=Action(
            tile_id=tile.tile_id,
            kind=ActionKind.REWORK,
            reason="defect found",
            confidence=0.9,
        ),
    )
    report = QCReport(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="op-1",
        started_at=datetime.now(UTC),
        status=BoardStatus.COMPLETE_REWORK,
        tile_reports=[tile_report],
    )
    assert report.defect_histogram == {DefectClass.PINHOLE: 1}

    with pytest.raises(ValueError, match="does not match"):
        QCReport(
            board_id="board-1",
            lot_id="lot-1",
            operator_id="op-1",
            started_at=datetime.now(UTC),
            status=BoardStatus.COMPLETE_REWORK,
            tile_reports=[tile_report],
            defect_histogram={DefectClass.SPUR: 5},
        )
