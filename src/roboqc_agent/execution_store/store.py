"""In-memory execution store used by tests and local development."""

from __future__ import annotations

from uuid import UUID

from roboqc_agent.execution_store.models import ExecutionEvent
from roboqc_agent.schemas import BoardStatus, QCReport


class InMemoryExecutionStore:
    """Persist board-level QC reports and append-only event timelines in memory."""

    def __init__(self) -> None:
        self.reports: dict[UUID, QCReport] = {}
        self.events: dict[UUID, list[ExecutionEvent]] = {}

    def add_event(self, event: ExecutionEvent) -> None:
        self.events.setdefault(event.report_id, []).append(event)

    def save_report(self, report: QCReport) -> None:
        self.reports[report.report_id] = report

    def get_report(self, report_id: UUID) -> QCReport | None:
        return self.reports.get(report_id)

    def get_timeline(self, report_id: UUID) -> list[ExecutionEvent]:
        return self.events.get(report_id, [])

    def metrics(self) -> dict[str, int]:
        hold_reports = sum(
            1 for report in self.reports.values() if report.status is BoardStatus.COMPLETE_HOLD
        )
        rework_reports = sum(
            1 for report in self.reports.values() if report.status is BoardStatus.COMPLETE_REWORK
        )
        completed_reports = sum(
            1 for report in self.reports.values() if report.status is not BoardStatus.IN_PROGRESS
        )
        timeline_events_total = sum(len(events) for events in self.events.values())
        return {
            "completed_reports": completed_reports,
            "hold_reports": hold_reports,
            "rework_reports": rework_reports,
            "timeline_events_total": timeline_events_total,
        }
