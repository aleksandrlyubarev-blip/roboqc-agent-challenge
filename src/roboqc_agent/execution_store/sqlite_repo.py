"""SQLite-backed repository for RoboQC evidence persistence."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from types import TracebackType
from uuid import UUID

from pydantic import ValidationError

from roboqc_agent.execution_store.models import ExecutionEvent
from roboqc_agent.schemas import BoardStatus, QCReport

logger = logging.getLogger(__name__)

DB_PATH_ENV_VAR = "ROBOQC_DB_PATH"


class SQLiteExecutionRepository:
    """Persist QC reports and event timelines in SQLite.

    The database path resolves from the ``db_path`` argument, then the
    ``ROBOQC_DB_PATH`` environment variable, then ``:memory:``. The in-memory
    fallback is for tests and local experiments only — production deployments
    must point at a persistent volume or reports are lost on restart.

    Thread-safe: the FastAPI surface serves requests from worker threads, so
    access to the shared connection is serialized with a lock.
    """

    def __init__(self, db_path: str | None = None) -> None:
        resolved = db_path or os.getenv(DB_PATH_ENV_VAR) or ":memory:"
        self.db_path = resolved
        if resolved != ":memory:":
            Path(resolved).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(resolved, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> SQLiteExecutionRepository:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _init_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS qc_reports (
                report_id TEXT PRIMARY KEY,
                board_id TEXT NOT NULL,
                lot_id TEXT NOT NULL,
                operator_id TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT
            )
            """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                event TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """)
        self.conn.commit()

    def add_event(self, event: ExecutionEvent) -> None:
        with self._lock:
            self._add_event_locked(event)

    def _add_event_locked(self, event: ExecutionEvent) -> None:
        self.conn.execute(
            """
            INSERT INTO events (report_id, event, payload_json, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(event.report_id),
                event.event,
                json.dumps(event.payload, ensure_ascii=False, sort_keys=True),
                event.timestamp,
            ),
        )
        self.conn.commit()

    def save_report(self, report: QCReport) -> None:
        with self._lock:
            self._save_report_locked(report)

    def _save_report_locked(self, report: QCReport) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO qc_reports
            (
                report_id,
                board_id,
                lot_id,
                operator_id,
                status,
                payload_json,
                started_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(report.report_id),
                report.board_id,
                report.lot_id,
                report.operator_id,
                report.status.value,
                report.model_dump_json(),
                report.started_at.isoformat(),
                None if report.completed_at is None else report.completed_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_report(self, report_id: UUID) -> QCReport | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT payload_json FROM qc_reports WHERE report_id = ?",
                (str(report_id),),
            ).fetchone()
        if row is None:
            return None
        try:
            return QCReport.model_validate_json(row[0])
        except ValidationError:
            logger.exception("Corrupted qc_reports payload for report_id=%s", report_id)
            return None

    def get_timeline(self, report_id: UUID) -> list[ExecutionEvent]:
        with self._lock:
            rows = self.conn.execute(
                """
            SELECT report_id, event, payload_json, timestamp
            FROM events
            WHERE report_id = ?
            ORDER BY id ASC
            """,
                (str(report_id),),
            ).fetchall()
        timeline: list[ExecutionEvent] = []
        for row in rows:
            try:
                payload = json.loads(row[2])
            except json.JSONDecodeError:
                logger.exception(
                    "Corrupted event payload for report_id=%s event=%s; skipping row",
                    report_id,
                    row[1],
                )
                continue
            timeline.append(
                ExecutionEvent(
                    report_id=UUID(row[0]),
                    event=row[1],
                    payload=payload,
                    timestamp=row[3],
                )
            )
        return timeline

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return self._metrics_locked()

    def _metrics_locked(self) -> dict[str, int]:
        completed_reports = self.conn.execute(
            "SELECT COUNT(*) FROM qc_reports WHERE status != ?",
            (BoardStatus.IN_PROGRESS.value,),
        ).fetchone()[0]
        hold_reports = self.conn.execute(
            "SELECT COUNT(*) FROM qc_reports WHERE status = ?",
            (BoardStatus.COMPLETE_HOLD.value,),
        ).fetchone()[0]
        rework_reports = self.conn.execute(
            "SELECT COUNT(*) FROM qc_reports WHERE status = ?",
            (BoardStatus.COMPLETE_REWORK.value,),
        ).fetchone()[0]
        timeline_events_total = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {
            "completed_reports": int(completed_reports),
            "hold_reports": int(hold_reports),
            "rework_reports": int(rework_reports),
            "timeline_events_total": int(timeline_events_total),
        }
