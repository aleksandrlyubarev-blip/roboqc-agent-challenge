"""ADK factory for the FMEA Risk agent.

The model maps each detected defect to severity, default action, justification,
and a senior-escalation flag, but it does not echo defect identities. The
factory declares ``FMEAObservation`` as the per-defect structured output and
``to_fmea_entries`` re-attaches each observation to its ``Defect`` by input
order (architecture §2.2: one entry per defect, same order).
"""

from __future__ import annotations

from collections.abc import Sequence

from google.adk.agents.llm_agent import Agent
from pydantic import BaseModel, Field

from roboqc_agent.schemas import ActionKind, Defect, FMEAEntry, Severity

FMEA_RISK_NAME = "fmea_risk"


class FMEAObservation(BaseModel):
    """FMEA mapping for one defect, before defect linkage."""

    severity: Severity
    default_action: ActionKind
    justification: str = Field(
        description="One operator-readable sentence, shown verbatim and stored in evidence"
    )
    escalate_to_senior: bool = Field(default=False)


def build_fmea_risk_agent(
    *,
    instruction: str,
    model: str = "gemini-2.5-pro",
) -> Agent:
    """Build the text-only FMEA Risk agent without owning prompt text."""

    return Agent(
        name=FMEA_RISK_NAME,
        description="Maps detected SMT defects to FMEA severity and default action.",
        model=model,
        instruction=instruction,
        output_schema=list[FMEAObservation],
        include_contents="none",
    )


def to_fmea_entries(
    observations: Sequence[FMEAObservation],
    defects: Sequence[Defect],
) -> list[FMEAEntry]:
    """Re-attach FMEA observations to their defects by input order.

    Pairs are formed positionally; any trailing, unmatched observation or defect
    is dropped, keeping the contract "one entry per resolved defect".
    """

    entries: list[FMEAEntry] = []
    for obs, defect in zip(observations, defects, strict=False):
        entries.append(
            FMEAEntry(
                defect_id=defect.defect_id,
                severity=obs.severity,
                default_action=obs.default_action,
                justification=obs.justification,
                escalate_to_senior=obs.escalate_to_senior,
            )
        )
    return entries


__all__ = [
    "FMEA_RISK_NAME",
    "FMEAObservation",
    "build_fmea_risk_agent",
    "to_fmea_entries",
]
