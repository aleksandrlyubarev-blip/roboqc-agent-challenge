from __future__ import annotations

from datetime import UTC, datetime

from roboqc_agent.execution_store import (
    ExecutionEvent,
    InMemoryExecutionStore,
    SQLiteExecutionRepository,
)
from roboqc_agent.schemas import BoardStatus, QCReport


def _report() -> QCReport:
    return QCReport(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="op-1",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        status=BoardStatus.COMPLETE_HOLD,
        tile_reports=[],
    )


def test_in_memory_execution_store_tracks_qc_reports() -> None:
    store = InMemoryExecutionStore()
    report = _report()
    store.save_report(report)
    store.add_event(ExecutionEvent(report_id=report.report_id, event="report_created"))

    assert store.get_report(report.report_id) == report
    assert store.metrics()["hold_reports"] == 1
    assert len(store.get_timeline(report.report_id)) == 1


def test_sqlite_execution_repository_round_trips_qc_report() -> None:
    repo = SQLiteExecutionRepository()
    report = _report()
    repo.save_report(report)
    repo.add_event(ExecutionEvent(report_id=report.report_id, event="report_created"))

    restored = repo.get_report(report.report_id)

    assert restored == report
    assert repo.metrics()["completed_reports"] == 1
    assert repo.get_timeline(report.report_id)[0].event == "report_created"
