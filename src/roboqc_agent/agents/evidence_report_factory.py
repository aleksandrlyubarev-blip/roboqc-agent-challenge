"""ADK factory for the Evidence Report agent."""

from __future__ import annotations

from collections import Counter

from google.adk.agents.llm_agent import Agent

from roboqc_agent.prompts.evidence_report import SYSTEM_PROMPT
from roboqc_agent.schemas import DefectClass, QCReport

EVIDENCE_REPORT_NAME = "evidence_report"


def build_evidence_report_agent(
    *,
    instruction: str = SYSTEM_PROMPT,
    model: str = "gemini-2.5-pro",
) -> Agent:
    """Build the Evidence Report agent."""

    return Agent(
        name=EVIDENCE_REPORT_NAME,
        description="Assembles board-level SMT inspection evidence reports.",
        model=model,
        instruction=instruction,
        output_schema=QCReport,
        include_contents="none",
    )


def compute_defect_histogram(report: QCReport) -> dict[DefectClass, int]:
    """Deterministically aggregate defect counts from a QCReport."""

    counter: Counter[DefectClass] = Counter()
    for tile_report in report.tile_reports:
        counter.update(defect.defect_class for defect in tile_report.defects)
    return dict(counter)


__all__ = [
    "EVIDENCE_REPORT_NAME",
    "build_evidence_report_agent",
    "compute_defect_histogram",
]
