from __future__ import annotations

from roboqc_agent.policy import FrictionPolicyEngine, PolicyCode, PolicyInput
from roboqc_agent.schemas import ActionKind, DefectClass, Severity


def test_low_confidence_routes_to_human_review() -> None:
    decision = FrictionPolicyEngine().evaluate(
        PolicyInput(
            defect_class=DefectClass.OPEN_TRACE,
            severity=Severity.CRITICAL,
            confidence=0.79,
        )
    )

    assert decision.action is ActionKind.HUMAN_REVIEW
    assert decision.code is PolicyCode.LOW_CONFIDENCE
    assert decision.requires_senior_review is True


def test_tombstoning_always_escalates() -> None:
    decision = FrictionPolicyEngine().evaluate(
        PolicyInput(
            defect_class=DefectClass.TOMBSTONING,
            severity=Severity.CRITICAL,
            confidence=0.99,
        )
    )

    assert decision.action is ActionKind.HOLD
    assert decision.code is PolicyCode.ALWAYS_ESCALATE_DEFECT
    assert decision.requires_senior_review is True


def test_major_defect_with_mid_confidence_reworks_and_flags_review() -> None:
    decision = FrictionPolicyEngine().evaluate(
        PolicyInput(
            defect_class=DefectClass.EXCESS_COPPER,
            severity=Severity.MAJOR,
            confidence=0.90,
        )
    )

    assert decision.action is ActionKind.REWORK
    assert decision.code is PolicyCode.MAJOR_DEFECT
    assert decision.requires_senior_review is True


def test_minor_high_confidence_defect_passes_without_extra_review() -> None:
    decision = FrictionPolicyEngine().evaluate(
        PolicyInput(
            defect_class=DefectClass.SPUR,
            severity=Severity.MINOR,
            confidence=0.97,
        )
    )

    assert decision.action is ActionKind.PASS
    assert decision.code is PolicyCode.MINOR_DEFECT
    assert decision.requires_senior_review is False
