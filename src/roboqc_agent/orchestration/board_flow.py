"""Board-level flow coordination: policy enforcement, aggregation, persistence.

This module closes the gap between the per-tile agent chain and the evidence
record:

* ``resolve_tile_action`` is the deterministic enforcement layer around the
  Supervisor LLM — it derives the tile action from the FrictionPolicyEngine
  and is used to validate (or replace) the LLM's proposal.
* ``BoardFlowCoordinator`` tracks expected tiles for a board, persists each
  finalized TileReport through the execution store, and assembles the final
  QCReport (with its deterministic histogram) once all tiles are complete.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from roboqc_agent.execution_store.models import ExecutionEvent
from roboqc_agent.policy.engine import FrictionPolicyEngine, PolicyDecision, PolicyInput
from roboqc_agent.schemas import (
    Action,
    ActionKind,
    BoardStatus,
    Defect,
    FMEAEntry,
    OperatorResponse,
    QCReport,
    TileReport,
)

# Worst-first precedence when aggregating several per-defect decisions into
# one tile action, and tile actions into a board status.
_ACTION_PRECEDENCE: dict[ActionKind, int] = {
    ActionKind.HOLD: 3,
    ActionKind.HUMAN_REVIEW: 2,
    ActionKind.REWORK: 1,
    ActionKind.PASS: 0,
}

_BOARD_STATUS_BY_ACTION: dict[ActionKind, BoardStatus] = {
    ActionKind.HOLD: BoardStatus.COMPLETE_HOLD,
    ActionKind.HUMAN_REVIEW: BoardStatus.COMPLETE_HOLD,
    ActionKind.REWORK: BoardStatus.COMPLETE_REWORK,
    ActionKind.PASS: BoardStatus.COMPLETE_PASS,
}


class ExecutionRepository(Protocol):
    """Persistence surface required by the coordinator."""

    def add_event(self, event: ExecutionEvent) -> None: ...

    def save_report(self, report: QCReport) -> None: ...


def resolve_tile_action(
    tile_id: UUID,
    defects: list[Defect],
    fmea_entries: list[FMEAEntry],
    *,
    engine: FrictionPolicyEngine | None = None,
) -> Action:
    """Derive the per-tile action deterministically from the policy engine.

    The Supervisor LLM proposes an Action; this function computes the policy
    ground truth so callers can accept the proposal when they agree or replace
    it when they don't. A tile without defects passes.
    """

    engine = engine or FrictionPolicyEngine()

    if not defects:
        return Action(
            tile_id=tile_id,
            kind=ActionKind.PASS,
            reason="No defects detected",
            triggered_hitl=False,
            confidence=1.0,
        )

    fmea_by_defect = {entry.defect_id: entry for entry in fmea_entries}
    missing = [str(d.defect_id) for d in defects if d.defect_id not in fmea_by_defect]
    if missing:
        raise ValueError(f"FMEA entries missing for defects: {', '.join(missing)}")

    worst: PolicyDecision | None = None
    escalate = False
    for defect in defects:
        entry = fmea_by_defect[defect.defect_id]
        decision = engine.evaluate(
            PolicyInput(
                defect_class=defect.defect_class,
                severity=entry.severity,
                confidence=defect.confidence,
            )
        )
        escalate = escalate or decision.requires_senior_review or entry.escalate_to_senior
        if worst is None or _ACTION_PRECEDENCE[decision.action] > _ACTION_PRECEDENCE[worst.action]:
            worst = decision

    assert worst is not None  # defects is non-empty
    return Action(
        tile_id=tile_id,
        kind=worst.action,
        reason=worst.reason,
        triggered_hitl=worst.action is ActionKind.HUMAN_REVIEW or escalate,
        confidence=max(defect.confidence for defect in defects),
    )


class BoardFlowCoordinator:
    """Collect finalized tiles for one board and emit the final QCReport.

    Resolves the graph-skeleton TODOs: the evidence report is only assembled
    once every expected tile is recorded, and every step is persisted through
    the execution store.
    """

    def __init__(
        self,
        *,
        board_id: str,
        lot_id: str,
        operator_id: str,
        expected_tiles: int,
        repository: ExecutionRepository,
        policy_engine: FrictionPolicyEngine | None = None,
    ) -> None:
        if expected_tiles <= 0:
            raise ValueError("expected_tiles must be positive")
        self.board_id = board_id
        self.lot_id = lot_id
        self.operator_id = operator_id
        self.expected_tiles = expected_tiles
        self.repository = repository
        self.policy_engine = policy_engine or FrictionPolicyEngine()
        self.started_at = datetime.now(UTC)
        self._tile_reports: list[TileReport] = []
        self._report_id: UUID | None = None
        self._finalized = False

    @property
    def is_complete(self) -> bool:
        return len(self._tile_reports) >= self.expected_tiles

    @property
    def tiles_recorded(self) -> int:
        return len(self._tile_reports)

    def record_tile(self, tile_report: TileReport) -> None:
        """Persist one finalized tile; enforce policy over the agent action."""

        if self._finalized:
            raise RuntimeError("Board flow already finalized")
        if tile_report.tile.board_id != self.board_id:
            raise ValueError(
                f"Tile belongs to board {tile_report.tile.board_id!r}, "
                f"coordinator tracks {self.board_id!r}"
            )

        policy_action = resolve_tile_action(
            tile_report.tile.tile_id,
            tile_report.defects,
            tile_report.fmea_entries,
            engine=self.policy_engine,
        )
        agent_action = tile_report.agent_action
        if (
            policy_action.kind is not agent_action.kind
            or policy_action.triggered_hitl != agent_action.triggered_hitl
        ):
            # The deterministic policy wins over the LLM proposal. Both the
            # routing kind and the HITL flag are enforced — a stale
            # triggered_hitl would silently skip a required senior review.
            tile_report = tile_report.model_copy(update={"agent_action": policy_action})

        self._tile_reports.append(tile_report)
        self.repository.add_event(
            ExecutionEvent(
                report_id=self._ensure_report_id(),
                event="tile_finalized",
                payload={
                    "tile_id": str(tile_report.tile.tile_id),
                    "action": tile_report.agent_action.kind.value,
                    "tiles_recorded": len(self._tile_reports),
                    "tiles_expected": self.expected_tiles,
                },
            )
        )

    def record_operator_response(self, response: OperatorResponse) -> TileReport:
        """Attach the operator's HITL decision to a recorded tile.

        Tiles whose action carries ``triggered_hitl`` block board finalization
        until the operator accepts or overrides; this is the friction policy's
        human-in-the-loop gate.
        """

        if self._finalized:
            raise RuntimeError("Board flow already finalized")

        for index, tile_report in enumerate(self._tile_reports):
            if tile_report.tile.tile_id != response.tile_id:
                continue
            if tile_report.operator_response is not None:
                raise ValueError(f"Tile {response.tile_id} already has an operator response")
            updated = tile_report.model_copy(
                update={
                    "operator_response": response,
                    "finalized_at": datetime.now(UTC),
                }
            )
            self._tile_reports[index] = updated
            self.repository.add_event(
                ExecutionEvent(
                    report_id=self._ensure_report_id(),
                    event="operator_response",
                    payload={
                        "tile_id": str(response.tile_id),
                        "operator_id": response.operator_id,
                        "action": response.action.value,
                        "final_kind": response.final_kind.value,
                    },
                )
            )
            return updated

        raise KeyError(f"Tile {response.tile_id} is not recorded for board {self.board_id}")

    def pending_hitl_tiles(self) -> list[TileReport]:
        """Tiles that still need an operator decision before finalization."""

        return [
            tr
            for tr in self._tile_reports
            if tr.agent_action.triggered_hitl and tr.operator_response is None
        ]

    def finalize(self) -> QCReport:
        """Assemble, persist, and return the board-level QCReport."""

        if not self.is_complete:
            raise RuntimeError(
                f"Cannot finalize: {len(self._tile_reports)}/{self.expected_tiles} "
                "tiles recorded"
            )
        if self._finalized:
            raise RuntimeError("Board flow already finalized")
        pending = self.pending_hitl_tiles()
        if pending:
            tile_ids = ", ".join(str(tr.tile.tile_id) for tr in pending)
            raise RuntimeError(f"Cannot finalize: operator decision pending for tiles: {tile_ids}")

        worst_kind = max(
            (self._effective_kind(tr) for tr in self._tile_reports),
            key=lambda kind: _ACTION_PRECEDENCE[kind],
        )
        signoff_times = [
            tr.operator_response.responded_at
            for tr in self._tile_reports
            if tr.operator_response is not None
        ]
        report = QCReport(
            report_id=self._ensure_report_id(),
            board_id=self.board_id,
            lot_id=self.lot_id,
            operator_id=self.operator_id,
            started_at=self.started_at,
            completed_at=datetime.now(UTC),
            status=_BOARD_STATUS_BY_ACTION[worst_kind],
            tile_reports=list(self._tile_reports),
            senior_escalations=[
                tr.tile.tile_id for tr in self._tile_reports if tr.agent_action.triggered_hitl
            ],
            operator_signoff_at=max(signoff_times) if signoff_times else None,
        )
        self.repository.save_report(report)
        self.repository.add_event(
            ExecutionEvent(
                report_id=report.report_id,
                event="board_finalized",
                payload={
                    "status": report.status.value,
                    "defect_histogram": {k.value: v for k, v in report.defect_histogram.items()},
                },
            )
        )
        self._finalized = True
        return report

    @staticmethod
    def _effective_kind(tile_report: TileReport) -> ActionKind:
        """Operator's final decision wins over the agent proposal."""

        if tile_report.operator_response is not None:
            return tile_report.operator_response.final_kind
        return tile_report.agent_action.kind

    def _ensure_report_id(self) -> UUID:
        if self._report_id is None:
            from uuid import uuid4

            self._report_id = uuid4()
        return self._report_id


__all__ = ["BoardFlowCoordinator", "ExecutionRepository", "resolve_tile_action"]
