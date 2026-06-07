from __future__ import annotations

from datetime import UTC, datetime

from roboqc_agent.agents.evidence_report import (
    EvidenceReporter,
    aggregate_board,
    aggregate_lot,
    assemble_tile_report,
    summarize_board,
)
from roboqc_agent.execution_store import InMemoryExecutionStore
from roboqc_agent.schemas import (
    Action,
    ActionKind,
    BBox,
    BoardStatus,
    Defect,
    DefectClass,
    LotStatus,
    QCReport,
    Tile,
    TileReport,
)


def _tile(board_id: str = "board-1", lot_id: str = "lot-1") -> Tile:
    return Tile(
        board_id=board_id,
        lot_id=lot_id,
        position={"row": 0, "col": 0},  # type: ignore[arg-type]
        magnification=10,
        image_uri="gs://demo/tile.png",
        captured_at=datetime.now(UTC),
        operator_id="op-1",
    )


def _tile_report(
    kind: ActionKind, *, triggered_hitl: bool = False, with_defect: bool = True
) -> TileReport:
    tile = _tile()
    defects: list[Defect] = []
    if with_defect:
        defects.append(
            Defect(
                tile_id=tile.tile_id,
                defect_class=DefectClass.SOLDER_BRIDGE,
                bbox=BBox(x=1, y=1, w=2, h=2),
                confidence=0.9,
                source="anomaly_arm",
            )
        )
    action = Action(
        tile_id=tile.tile_id,
        kind=kind,
        reason="test",
        triggered_hitl=triggered_hitl,
        confidence=0.9,
    )
    return assemble_tile_report(tile, defects, [], action)


def _board(status_kinds: list[ActionKind], *, signed_off: bool = True) -> QCReport:
    tile_reports = [_tile_report(kind) for kind in status_kinds]
    return aggregate_board(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="op-1",
        started_at=datetime.now(UTC),
        tile_reports=tile_reports,
        operator_signoff_at=datetime.now(UTC) if signed_off else None,
    )


def test_board_status_holds_when_any_tile_holds() -> None:
    report = _board([ActionKind.PASS, ActionKind.REWORK, ActionKind.HOLD])

    assert report.status is BoardStatus.COMPLETE_HOLD
    assert report.defect_histogram[DefectClass.SOLDER_BRIDGE] == 3


def test_board_status_reworks_when_no_hold() -> None:
    report = _board([ActionKind.PASS, ActionKind.REWORK])

    assert report.status is BoardStatus.COMPLETE_REWORK


def test_board_collects_senior_escalations() -> None:
    tile_reports = [
        _tile_report(ActionKind.HOLD, triggered_hitl=True),
        _tile_report(ActionKind.PASS, triggered_hitl=False),
    ]
    report = aggregate_board(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="op-1",
        started_at=datetime.now(UTC),
        tile_reports=tile_reports,
    )

    assert len(report.senior_escalations) == 1


def test_lot_holds_for_engineering_above_threshold() -> None:
    boards = [_board([ActionKind.PASS]) for _ in range(9)]
    boards.append(_board([ActionKind.HOLD]))  # 10% hold rate, not above
    boards.append(_board([ActionKind.HOLD]))  # now ~18%, above threshold

    summary = aggregate_lot("lot-1", boards)

    assert summary.status is LotStatus.HOLD_FOR_ENGINEERING
    assert summary.hold_count == 2


def test_lot_approved_when_clean() -> None:
    boards = [_board([ActionKind.PASS]) for _ in range(5)]

    summary = aggregate_lot("lot-1", boards)

    assert summary.status is LotStatus.APPROVED
    assert summary.pass_count == 5


def test_lot_in_progress_until_all_boards_signed_off() -> None:
    boards = [_board([ActionKind.PASS]) for _ in range(4)]
    boards.append(_board([ActionKind.PASS], signed_off=False))

    summary = aggregate_lot("lot-1", boards)

    assert summary.status is LotStatus.IN_PROGRESS
    assert summary.finalized_at is None


def test_persist_board_writes_report_and_event() -> None:
    store = InMemoryExecutionStore()
    reporter = EvidenceReporter(store)
    report = _board([ActionKind.HOLD])

    reporter.persist_board(report)

    assert store.get_report(report.report_id) is not None
    timeline = store.get_timeline(report.report_id)
    assert any(event.event == "board_finalized" for event in timeline)


def test_summarize_board_deterministic_without_provider() -> None:
    report = _board([ActionKind.HOLD])

    summary = summarize_board(report)

    assert "board-1" in summary
    assert "solder_bridge" in summary
