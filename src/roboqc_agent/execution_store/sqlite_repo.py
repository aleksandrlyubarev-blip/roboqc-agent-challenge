"""SQLite-backed repository for RoboQC evidence persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import UUID

from roboqc_agent.execution_store.models import ExecutionEvent
from roboqc_agent.schemas import QCReport


class SQLiteExecutionRepository:
    """Persist QC reports and event timelines in SQLite."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

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
        row = self.conn.execute(
            "SELECT payload_json FROM qc_reports WHERE report_id = ?",
            (str(report_id),),
        ).fetchone()
        if row is None:
            return None
        return QCReport.model_validate_json(row[0])

    def get_timeline(self, report_id: UUID) -> list[ExecutionEvent]:
        rows = self.conn.execute(
            """
            SELECT report_id, event, payload_json, timestamp
            FROM events
            WHERE report_id = ?
            ORDER BY id ASC
            """,
            (str(report_id),),
        ).fetchall()
        return [
            ExecutionEvent(
                report_id=UUID(row[0]),
                event=row[1],
                payload=json.loads(row[2]),
                timestamp=row[3],
            )
            for row in rows
        ]

    def metrics(self) -> dict[str, int]:
        completed_reports = self.conn.execute(
            "SELECT COUNT(*) FROM qc_reports WHERE status != 'in_progress'"
        ).fetchone()[0]
        hold_reports = self.conn.execute(
            "SELECT COUNT(*) FROM qc_reports WHERE status = 'hold'"
        ).fetchone()[0]
        rework_reports = self.conn.execute(
            "SELECT COUNT(*) FROM qc_reports WHERE status = 'rework'"
        ).fetchone()[0]
        timeline_events_total = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {
            "completed_reports": int(completed_reports),
            "hold_reports": int(hold_reports),
            "rework_reports": int(rework_reports),
            "timeline_events_total": int(timeline_events_total),
        }
