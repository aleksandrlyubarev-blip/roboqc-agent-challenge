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
    assert repo.metrics()["hold_reports"] == 1
    assert repo.get_timeline(report.report_id)[0].event == "report_created"


def test_sqlite_execution_repository_context_manager_closes_connection() -> None:
    import sqlite3

    import pytest

    with SQLiteExecutionRepository() as repo:
        repo.save_report(_report())
    with pytest.raises(sqlite3.ProgrammingError):
        repo.conn.execute("SELECT 1")


def test_sqlite_execution_repository_reads_db_path_from_env(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    db_file = tmp_path / "reports" / "roboqc.db"
    monkeypatch.setenv("ROBOQC_DB_PATH", str(db_file))

    with SQLiteExecutionRepository() as repo:
        report = _report()
        repo.save_report(report)

    assert db_file.exists()
    with SQLiteExecutionRepository(str(db_file)) as reopened:
        assert reopened.get_report(report.report_id) == report


def test_sqlite_execution_repository_tolerates_corrupted_rows() -> None:
    repo = SQLiteExecutionRepository()
    report = _report()
    repo.save_report(report)
    repo.add_event(ExecutionEvent(report_id=report.report_id, event="ok"))

    repo.conn.execute(
        'UPDATE qc_reports SET payload_json = \'{"not": "a report"}\' WHERE report_id = ?',
        (str(report.report_id),),
    )
    repo.conn.execute("UPDATE events SET payload_json = 'not json'")
    repo.conn.commit()

    assert repo.get_report(report.report_id) is None
    assert repo.get_timeline(report.report_id) == []
