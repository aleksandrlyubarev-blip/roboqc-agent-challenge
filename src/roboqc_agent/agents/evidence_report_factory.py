"""ADK factory for the Evidence Report agent."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from roboqc_agent.config import default_model
from roboqc_agent.prompts.evidence_report import SYSTEM_PROMPT
from roboqc_agent.schemas import DefectClass, QCReport
from roboqc_agent.schemas import compute_defect_histogram as _compute_histogram

EVIDENCE_REPORT_NAME = "evidence_report"
EVIDENCE_REPORT_STATE_KEY = "qc_report"


def build_evidence_report_agent(
    *,
    instruction: str = SYSTEM_PROMPT,
    model: str | None = None,
) -> Agent:
    """Build the Evidence Report agent.

    The QCReport schema itself recomputes the defect histogram and rejects
    mismatches, so an LLM response with a wrong aggregate fails validation.
    """

    return Agent(
        name=EVIDENCE_REPORT_NAME,
        description="Assembles board-level SMT inspection evidence reports.",
        model=model or default_model(),
        instruction=instruction,
        output_schema=QCReport,
        output_key=EVIDENCE_REPORT_STATE_KEY,
        include_contents="none",
    )


def compute_defect_histogram(report: QCReport) -> dict[DefectClass, int]:
    """Deterministically aggregate defect counts from a QCReport."""

    return _compute_histogram(report.tile_reports)


__all__ = [
    "EVIDENCE_REPORT_NAME",
    "EVIDENCE_REPORT_STATE_KEY",
    "build_evidence_report_agent",
    "compute_defect_histogram",
]
