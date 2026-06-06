from __future__ import annotations

from uuid import UUID, uuid4

from roboqc_agent.agents.supervisor import decide_action
from roboqc_agent.schemas import (
    ActionKind,
    BBox,
    Defect,
    DefectClass,
    FMEAEntry,
    Severity,
)


def _defect(
    tile_id: UUID,
    defect_class: DefectClass,
    confidence: float,
    source: str = "labeled_detector",
) -> Defect:
    return Defect(
        tile_id=tile_id,
        defect_class=defect_class,
        bbox=BBox(x=1, y=1, w=2, h=2),
        confidence=confidence,
        source=source,  # type: ignore[arg-type]
    )


def _fmea(
    defect: Defect, severity: Severity, action: ActionKind, escalate: bool = False
) -> FMEAEntry:
    return FMEAEntry(
        defect_id=defect.defect_id,
        severity=severity,
        default_action=action,
        justification="test",
        escalate_to_senior=escalate,
    )


def test_clean_tile_passes_with_full_confidence() -> None:
    action = decide_action(uuid4(), [], [])

    assert action.kind is ActionKind.PASS
    assert action.confidence == 1.0
    assert action.triggered_hitl is False


def test_critical_high_confidence_defect_holds() -> None:
    tile_id = uuid4()
    defect = _defect(tile_id, DefectClass.SHORT_CIRCUIT, 0.97)
    action = decide_action(tile_id, [defect], [_fmea(defect, Severity.CRITICAL, ActionKind.HOLD)])

    assert action.kind is ActionKind.HOLD
    assert action.triggered_hitl is False
    assert action.confidence == 0.97


def test_low_confidence_defect_routes_to_human_review() -> None:
    tile_id = uuid4()
    defect = _defect(tile_id, DefectClass.OPEN_TRACE, 0.60)
    action = decide_action(tile_id, [defect], [_fmea(defect, Severity.CRITICAL, ActionKind.HOLD)])

    assert action.kind is ActionKind.HUMAN_REVIEW
    assert action.triggered_hitl is True


def test_minor_high_confidence_defect_passes() -> None:
    tile_id = uuid4()
    defect = _defect(tile_id, DefectClass.SPUR, 0.97)
    action = decide_action(tile_id, [defect], [_fmea(defect, Severity.MINOR, ActionKind.PASS)])

    assert action.kind is ActionKind.PASS
    assert action.triggered_hitl is False


def test_uncertain_defect_overrides_confident_critical() -> None:
    tile_id = uuid4()
    critical = _defect(tile_id, DefectClass.SHORT_CIRCUIT, 0.97)
    uncertain = _defect(tile_id, DefectClass.MOUSEBITE, 0.60)
    action = decide_action(
        tile_id,
        [critical, uncertain],
        [
            _fmea(critical, Severity.CRITICAL, ActionKind.HOLD),
            _fmea(uncertain, Severity.MAJOR, ActionKind.REWORK),
        ],
    )

    # Any uncertain defect routes the whole tile to a human.
    assert action.kind is ActionKind.HUMAN_REVIEW
    assert action.triggered_hitl is True
    assert action.confidence == 0.97


def test_escalate_flag_sets_hitl_without_changing_action() -> None:
    tile_id = uuid4()
    defect = _defect(tile_id, DefectClass.TOMBSTONING, 0.99, source="anomaly_arm")
    action = decide_action(
        tile_id,
        [defect],
        [_fmea(defect, Severity.CRITICAL, ActionKind.HOLD, escalate=True)],
    )

    assert action.kind is ActionKind.HOLD
    assert action.triggered_hitl is True
