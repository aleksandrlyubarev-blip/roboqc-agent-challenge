"""Confidence-aware inspection policy for SMT first-article review."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from roboqc_agent.schemas import ActionKind, DefectClass, Severity


class PolicyCode(StrEnum):
    """Stable reason codes emitted by the inspection policy."""

    LOW_CONFIDENCE = "low_confidence"
    ALWAYS_ESCALATE_DEFECT = "always_escalate_defect"
    CRITICAL_DEFECT = "critical_defect"
    MAJOR_DEFECT = "major_defect"
    MINOR_DEFECT = "minor_defect"


class PolicyInput(BaseModel):
    """Inputs already resolved by Vision Inspector and FMEA Risk."""

    model_config = ConfigDict(strict=True)

    defect_class: DefectClass
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)


class PolicyDecision(BaseModel):
    """Supervisor-facing policy output for one defect."""

    model_config = ConfigDict(strict=True)

    action: ActionKind
    code: PolicyCode
    reason: str
    requires_senior_review: bool = False


class FrictionPolicyEngine:
    """Map defect severity and confidence to the next inspection action."""

    low_confidence_threshold: float = 0.80
    senior_review_threshold: float = 0.95
    always_escalate_defects: frozenset[DefectClass] = frozenset({DefectClass.TOMBSTONING})

    def evaluate(self, payload: PolicyInput) -> PolicyDecision:
        if payload.confidence < self.low_confidence_threshold:
            return PolicyDecision(
                action=ActionKind.HUMAN_REVIEW,
                code=PolicyCode.LOW_CONFIDENCE,
                reason="Confidence below automatic decision threshold",
                requires_senior_review=True,
            )

        if payload.defect_class in self.always_escalate_defects:
            return PolicyDecision(
                action=ActionKind.HOLD,
                code=PolicyCode.ALWAYS_ESCALATE_DEFECT,
                reason="Defect class always escalates during first-article inspection",
                requires_senior_review=True,
            )

        action_by_severity = {
            Severity.CRITICAL: ActionKind.HOLD,
            Severity.MAJOR: ActionKind.REWORK,
            Severity.MINOR: ActionKind.PASS,
        }
        code_by_severity = {
            Severity.CRITICAL: PolicyCode.CRITICAL_DEFECT,
            Severity.MAJOR: PolicyCode.MAJOR_DEFECT,
            Severity.MINOR: PolicyCode.MINOR_DEFECT,
        }

        return PolicyDecision(
            action=action_by_severity[payload.severity],
            code=code_by_severity[payload.severity],
            reason=f"{payload.severity.value.capitalize()} defect policy",
            requires_senior_review=payload.confidence < self.senior_review_threshold,
        )
