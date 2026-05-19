from datetime import UTC, datetime

from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.evidence_report_factory import (
    EVIDENCE_REPORT_NAME,
    build_evidence_report_agent,
    compute_defect_histogram,
)
from roboqc_agent.prompts.evidence_report import SYSTEM_PROMPT
from roboqc_agent.schemas import BoardStatus, QCReport


def test_build_evidence_report_agent_uses_prompt_constant() -> None:
    agent = build_evidence_report_agent()

    assert isinstance(agent, Agent)
    assert agent.name == EVIDENCE_REPORT_NAME
    assert agent.instruction == SYSTEM_PROMPT
    assert agent.output_schema is QCReport
    assert agent.include_contents == "none"


def test_compute_defect_histogram_handles_empty_report() -> None:
    report = QCReport(
        board_id="board-1",
        lot_id="lot-1",
        operator_id="operator-1",
        started_at=datetime.now(UTC),
        status=BoardStatus.IN_PROGRESS,
        tile_reports=[],
    )

    assert compute_defect_histogram(report) == {}
