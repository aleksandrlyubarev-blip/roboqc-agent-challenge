from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from roboqc_agent.execution_store import SQLiteExecutionRepository
from roboqc_agent.orchestration.board_flow import BoardFlowCoordinator, resolve_tile_action
from roboqc_agent.schemas import (
    Action,
    ActionKind,
    BBox,
    BoardStatus,
    Defect,
    DefectClass,
    FMEAEntry,
    Severity,
    Tile,
    TilePosition,
    TileReport,
)


def _tile(board_id: str = "board-1") -> Tile:
    return Tile(
        board_id=board_id,
        lot_id="lot-1",
        position=TilePosition(row=0, col=0),
        magnification=10,
        image_uri="gs://demo/tile.png",
        captured_at=datetime.now(UTC),
        operator_id="op-1",
    )


def _defect(tile_id, defect_class=DefectClass.OPEN_TRACE, confidence=0.9):  # type: ignore[no-untyped-def]
    return Defect(
        tile_id=tile_id,
        defect_class=defect_class,
        bbox=BBox(x=1, y=1, w=2, h=2),
        confidence=confidence,
        source="labeled_detector",
    )


def _fmea(defect, severity=Severity.MAJOR):  # type: ignore[no-untyped-def]
    return FMEAEntry(
        defect_id=defect.defect_id,
        severity=severity,
        default_action=ActionKind.REWORK,
        justification="test entry",
    )


def test_resolve_tile_action_passes_clean_tile() -> None:
    action = resolve_tile_action(uuid4(), [], [])
    assert action.kind is ActionKind.PASS
    assert not action.triggered_hitl


def test_resolve_tile_action_picks_worst_decision() -> None:
    tile = _tile()
    minor = _defect(tile.tile_id, confidence=0.99)
    critical = _defect(tile.tile_id, DefectClass.SHORT_CIRCUIT, confidence=0.97)
    entries = [_fmea(minor, Severity.MINOR), _fmea(critical, Severity.CRITICAL)]

    action = resolve_tile_action(tile.tile_id, [minor, critical], entries)

    assert action.kind is ActionKind.HOLD
    assert action.confidence == pytest.approx(0.99)


def test_resolve_tile_action_low_confidence_routes_to_human() -> None:
    tile = _tile()
    defect = _defect(tile.tile_id, confidence=0.5)
    action = resolve_tile_action(tile.tile_id, [defect], [_fmea(defect)])
    assert action.kind is ActionKind.HUMAN_REVIEW
    assert action.triggered_hitl


def test_resolve_tile_action_requires_fmea_coverage() -> None:
    tile = _tile()
    defect = _defect(tile.tile_id)
    with pytest.raises(ValueError, match="FMEA entries missing"):
        resolve_tile_action(tile.tile_id, [defect], [])


def _tile_report(action_kind: ActionKind = ActionKind.PASS) -> TileReport:
    tile = _tile()
    if action_kind is ActionKind.PASS:
        defects: list[Defect] = []
        entries: list[FMEAEntry] = []
    else:
        defect = _defect(tile.tile_id, confidence=0.97)
        severity = Severity.CRITICAL if action_kind is ActionKind.HOLD else Severity.MAJOR
        defects = [defect]
        entries = [_fmea(defect, severity)]
    return TileReport(
        tile=tile,
        defects=defects,
        fmea_entries=entries,
        agent_action=Action(
            tile_id=tile.tile_id,
            kind=action_kind,
            reason="agent proposal",
            confidence=0.97,
        ),
    )


def test_coordinator_finalizes_board_after_all_tiles() -> None:
    repo = SQLiteExecutionRepository()
    coordinator = BoardFlowCoordinator(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="op-1",
        expected_tiles=2,
        repository=repo,
    )

    coordinator.record_tile(_tile_report(ActionKind.PASS))
    assert not coordinator.is_complete
    with pytest.raises(RuntimeError, match="Cannot finalize"):
        coordinator.finalize()

    coordinator.record_tile(_tile_report(ActionKind.REWORK))
    report = coordinator.finalize()

    assert report.status is BoardStatus.COMPLETE_REWORK
    assert report.defect_histogram == {DefectClass.OPEN_TRACE: 1}
    assert repo.get_report(report.report_id) == report
    events = [event.event for event in repo.get_timeline(report.report_id)]
    assert events == ["tile_finalized", "tile_finalized", "board_finalized"]


def test_coordinator_overrides_llm_action_with_policy() -> None:
    repo = SQLiteExecutionRepository()
    coordinator = BoardFlowCoordinator(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="op-1",
        expected_tiles=1,
        repository=repo,
    )

    # LLM proposed PASS, but the tile carries a critical defect → policy HOLD.
    tile_report = _tile_report(ActionKind.HOLD).model_copy()
    lenient = tile_report.agent_action.model_copy(update={"kind": ActionKind.PASS})
    coordinator.record_tile(tile_report.model_copy(update={"agent_action": lenient}))

    report = coordinator.finalize()
    assert report.status is BoardStatus.COMPLETE_HOLD
    assert report.tile_reports[0].agent_action.kind is ActionKind.HOLD


def test_coordinator_rejects_foreign_board_tiles() -> None:
    coordinator = BoardFlowCoordinator(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="op-1",
        expected_tiles=1,
        repository=SQLiteExecutionRepository(),
    )
    foreign = _tile_report()
    foreign = foreign.model_copy(update={"tile": _tile(board_id="board-2")})
    with pytest.raises(ValueError, match="board"):
        coordinator.record_tile(foreign)
