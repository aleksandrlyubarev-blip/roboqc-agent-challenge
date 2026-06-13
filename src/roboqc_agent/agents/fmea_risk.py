"""ADK factory for the FMEA Risk agent."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from roboqc_agent.config import default_model
from roboqc_agent.prompts.fmea_risk import SYSTEM_PROMPT
from roboqc_agent.schemas import FMEAEntry

FMEA_RISK_NAME = "fmea_risk"
FMEA_RISK_STATE_KEY = "fmea_entries"


def build_fmea_risk_agent(
    *,
    instruction: str = SYSTEM_PROMPT,
    model: str | None = None,
) -> Agent:
    """Build the text-only FMEA Risk agent."""

    return Agent(
        name=FMEA_RISK_NAME,
        description="Maps detected SMT defects to FMEA severity and default action.",
        model=model or default_model(),
        instruction=instruction,
        output_schema=list[FMEAEntry],
        output_key=FMEA_RISK_STATE_KEY,
        include_contents="none",
    )


__all__ = ["FMEA_RISK_NAME", "FMEA_RISK_STATE_KEY", "build_fmea_risk_agent"]
