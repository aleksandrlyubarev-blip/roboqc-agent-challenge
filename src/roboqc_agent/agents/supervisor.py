"""Supervisor — the final per-tile decision node.

Per architecture §2.4 and §6 the Supervisor is deterministic: it runs every
(defect, FMEA entry) pair through the friction policy engine and aggregates the
per-defect policy decisions into a single tile-level ``Action``. The rationale
text is generated deterministically for v1 (architecture §13.3) to keep a Gemini
call off the per-tile critical path.

Aggregation rule: a tile takes the most conservative action any of its defects
demands. Action precedence (most-stopping first) is
``human_review > hold > rework > pass`` — so any uncertain (low-confidence)
defect routes the whole tile to a human, which is the safe default for
first-article inspection.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from roboqc_agent.policy import FrictionPolicyEngine, PolicyDecision, PolicyInput
from roboqc_agent.schemas import Action, ActionKind, Defect, FMEAEntry

SUPERVISOR_NAME = "supervisor"

# Most-stopping first. ``index`` gives a sortable precedence (lower == more
# conservative), so the tile action is the minimum-index action across defects.
_ACTION_PRECEDENCE: tuple[ActionKind, ...] = (
    ActionKind.HUMAN_REVIEW,
    ActionKind.HOLD,
    ActionKind.REWORK,
    ActionKind.PASS,
)


def _precedence(action: ActionKind) -> int:
    return _ACTION_PRECEDENCE.index(action)


def decide_action(
    tile_id: UUID,
    defects: Sequence[Defect],
    fmea_entries: Sequence[FMEAEntry],
    *,
    policy: FrictionPolicyEngine | None = None,
) -> Action:
    """Issue the final per-tile ``Action`` from defects and their FMEA entries."""

    policy = policy or FrictionPolicyEngine()

    if not defects:
        return Action(
            tile_id=tile_id,
            kind=ActionKind.PASS,
            reason="Clean tile: no defects detected.",
            triggered_hitl=False,
            confidence=1.0,
        )

    aggregate_confidence = max(defect.confidence for defect in defects)
    confidence_by_defect = {defect.defect_id: defect.confidence for defect in defects}
    class_by_defect = {defect.defect_id: defect.defect_class for defect in defects}

    decisions: list[tuple[FMEAEntry, PolicyDecision]] = []
    for entry in fmea_entries:
        if entry.defect_id not in class_by_defect:
            # FMEA entry without a matching defect — treat as upstream noise.
            continue
        decisions.append(
            (
                entry,
                policy.evaluate(
                    PolicyInput(
                        defect_class=class_by_defect[entry.defect_id],
                        severity=entry.severity,
                        confidence=confidence_by_defect[entry.defect_id],
                    )
                ),
            )
        )

    if not decisions:
        # Defects exist but none could be risk-mapped: route to a human.
        return Action(
            tile_id=tile_id,
            kind=ActionKind.HUMAN_REVIEW,
            reason="Defects detected but not risk-mapped; operator review required.",
            triggered_hitl=True,
            confidence=aggregate_confidence,
        )

    kind = min(
        (decision.action for _, decision in decisions),
        key=_precedence,
    )
    triggered_hitl = (
        kind is ActionKind.HUMAN_REVIEW
        or any(decision.requires_senior_review for _, decision in decisions)
        or any(entry.escalate_to_senior for entry, _ in decisions)
    )

    return Action(
        tile_id=tile_id,
        kind=kind,
        reason=_build_reason(kind, decisions, defect_count=len(defects)),
        triggered_hitl=triggered_hitl,
        confidence=aggregate_confidence,
    )


def _build_reason(
    kind: ActionKind,
    decisions: list[tuple[FMEAEntry, PolicyDecision]],
    *,
    defect_count: int,
) -> str:
    """Deterministic two-sentence rationale citing the decision driver."""

    driver = min(
        (decision for _, decision in decisions),
        key=lambda decision: _precedence(decision.action),
    )
    plural = "defect" if defect_count == 1 else "defects"
    senior = sum(1 for _, decision in decisions if decision.requires_senior_review)
    senior_note = f" {senior} flagged for senior review." if senior else ""
    return (
        f"{kind.value.upper()}: {driver.reason.lower()}. "
        f"{defect_count} {plural} on tile.{senior_note}"
    )


__all__ = ["SUPERVISOR_NAME", "decide_action"]
