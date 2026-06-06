"""Evidence Report — assembles and aggregates the audit trail.

This agent is primarily code, not an LLM (architecture §2.3). It assembles a
per-tile ``TileReport`` from upstream outputs, aggregates tiles into a
board-level ``QCReport`` and boards into a ``LotSummary``, and persists the
board record behind the execution-store boundary. The only optional LLM surface
is the human-readable board summary (``summarize_board``).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from roboqc_agent.execution_store.models import ExecutionEvent
from roboqc_agent.schemas import (
    Action,
    ActionKind,
    BoardStatus,
    Defect,
    DefectClass,
    FMEAEntry,
    LotStatus,
    LotSummary,
    OperatorResponse,
    QCReport,
    Tile,
    TileReport,
)

if TYPE_CHECKING:
    from roboqc_agent.providers.vertex_gemini import VertexGeminiProvider

# Lot hold-rate above this fraction routes the lot to engineering review (§4).
LOT_HOLD_THRESHOLD = 0.10


class EvidenceStore(Protocol):
    """Minimal persistence surface shared by the in-memory and SQLite stores."""

    def add_event(self, event: ExecutionEvent) -> None: ...

    def save_report(self, report: QCReport) -> None: ...


def assemble_tile_report(
    tile: Tile,
    defects: Sequence[Defect],
    fmea_entries: Sequence[FMEAEntry],
    action: Action,
    *,
    operator_response: OperatorResponse | None = None,
    finalized_at: datetime | None = None,
) -> TileReport:
    """Assemble the immutable per-tile evidence record (pure aggregation)."""

    return TileReport(
        tile=tile,
        defects=list(defects),
        fmea_entries=list(fmea_entries),
        agent_action=action,
        operator_response=operator_response,
        finalized_at=finalized_at,
    )


def _effective_kind(report: TileReport) -> ActionKind:
    """The action that actually governs a tile: operator's if they responded."""

    if report.operator_response is not None:
        return report.operator_response.final_kind
    return report.agent_action.kind


def _board_status(tile_reports: Sequence[TileReport]) -> BoardStatus:
    kinds = [_effective_kind(report) for report in tile_reports]
    # Unresolved human_review is treated conservatively as a hold: a tile the
    # operator has not cleared must not let the board pass automatically.
    if any(kind in (ActionKind.HOLD, ActionKind.HUMAN_REVIEW) for kind in kinds):
        return BoardStatus.COMPLETE_HOLD
    if any(kind is ActionKind.REWORK for kind in kinds):
        return BoardStatus.COMPLETE_REWORK
    return BoardStatus.COMPLETE_PASS


def _defect_histogram(tile_reports: Sequence[TileReport]) -> dict[DefectClass, int]:
    histogram: dict[DefectClass, int] = {}
    for report in tile_reports:
        for defect in report.defects:
            histogram[defect.defect_class] = histogram.get(defect.defect_class, 0) + 1
    return histogram


def aggregate_board(
    *,
    board_id: str,
    lot_id: str,
    operator_id: str,
    started_at: datetime,
    tile_reports: Sequence[TileReport],
    completed_at: datetime | None = None,
    operator_signoff_at: datetime | None = None,
    report_id: UUID | None = None,
) -> QCReport:
    """Aggregate tile reports into a board-level ``QCReport`` (architecture §4)."""

    reports = list(tile_reports)
    senior_escalations = [
        report.tile.tile_id for report in reports if report.agent_action.triggered_hitl
    ]
    qc_report = QCReport(
        board_id=board_id,
        lot_id=lot_id,
        operator_id=operator_id,
        started_at=started_at,
        completed_at=completed_at if completed_at is not None else datetime.now(UTC),
        status=_board_status(reports),
        tile_reports=reports,
        defect_histogram=_defect_histogram(reports),
        senior_escalations=senior_escalations,
        operator_signoff_at=operator_signoff_at,
    )
    if report_id is not None:
        qc_report = qc_report.model_copy(update={"report_id": report_id})
    return qc_report


def aggregate_lot(lot_id: str, qc_reports: Sequence[QCReport]) -> LotSummary:
    """Roll boards up into a ``LotSummary`` (architecture §4)."""

    reports = list(qc_reports)
    pass_count = sum(1 for r in reports if r.status is BoardStatus.COMPLETE_PASS)
    rework_count = sum(1 for r in reports if r.status is BoardStatus.COMPLETE_REWORK)
    hold_count = sum(1 for r in reports if r.status is BoardStatus.COMPLETE_HOLD)

    total = len(reports)
    # A lot is only APPROVED/HOLD once every board is complete AND signed off by
    # the operator (operator_workflow.md §4: "after all boards are signed off").
    not_signed_off = any(r.operator_signoff_at is None for r in reports)
    if total == 0 or any(r.status is BoardStatus.IN_PROGRESS for r in reports) or not_signed_off:
        status = LotStatus.IN_PROGRESS
    elif hold_count / total > LOT_HOLD_THRESHOLD:
        status = LotStatus.HOLD_FOR_ENGINEERING
    else:
        status = LotStatus.APPROVED

    return LotSummary(
        lot_id=lot_id,
        boards=[r.board_id for r in reports],
        pass_count=pass_count,
        rework_count=rework_count,
        hold_count=hold_count,
        status=status,
        finalized_at=datetime.now(UTC) if status is not LotStatus.IN_PROGRESS else None,
    )


def summarize_board(
    report: QCReport,
    *,
    provider: VertexGeminiProvider | None = None,
    instruction: str | None = None,
) -> str:
    """Human-readable board summary; deterministic unless a provider is given."""

    if provider is not None and instruction is not None:
        payload = f"{instruction}\n\nQC report JSON:\n{report.model_dump_json()}"
        result = provider.generate_text(payload)
        if result.text:
            return result.text.strip()

    histogram = ", ".join(f"{cls.value}×{count}" for cls, count in report.defect_histogram.items())
    escalations = len(report.senior_escalations)
    escalation_note = f" {escalations} tile(s) escalated for senior review." if escalations else ""
    return (
        f"Board {report.board_id}: {report.status.value} "
        f"across {len(report.tile_reports)} tiles. "
        f"Defects: {histogram or 'none'}.{escalation_note}"
    )


class EvidenceReporter:
    """Persists board-level evidence and an append-only event timeline."""

    def __init__(self, store: EvidenceStore) -> None:
        self.store = store

    def persist_board(self, report: QCReport) -> QCReport:
        """Save the board report and record a finalization event."""

        self.store.save_report(report)
        self.store.add_event(
            ExecutionEvent(
                report_id=report.report_id,
                event="board_finalized",
                payload={
                    "board_id": report.board_id,
                    "status": report.status.value,
                    "tile_count": len(report.tile_reports),
                    "senior_escalations": len(report.senior_escalations),
                },
            )
        )
        return report


__all__ = [
    "LOT_HOLD_THRESHOLD",
    "EvidenceStore",
    "EvidenceReporter",
    "assemble_tile_report",
    "aggregate_board",
    "aggregate_lot",
    "summarize_board",
]
