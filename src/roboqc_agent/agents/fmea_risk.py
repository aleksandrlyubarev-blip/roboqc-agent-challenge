"""ADK factory for the FMEA Risk agent."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from roboqc_agent.prompts.fmea_risk import SYSTEM_PROMPT
from roboqc_agent.schemas import FMEAEntry

FMEA_RISK_NAME = "fmea_risk"


def build_fmea_risk_agent(
    *,
    instruction: str = SYSTEM_PROMPT,
    model: str = "gemini-2.5-pro",
) -> Agent:
    """Build the text-only FMEA Risk agent."""

    return Agent(
        name=FMEA_RISK_NAME,
        description="Maps detected SMT defects to FMEA severity and default action.",
        model=model,
        instruction=instruction,
        output_schema=list[FMEAEntry],
        include_contents="none",
    )


__all__ = ["FMEA_RISK_NAME", "build_fmea_risk_agent"]
