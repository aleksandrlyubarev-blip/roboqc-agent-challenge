"""ADK factory for the Supervisor agent."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from roboqc_agent.prompts.supervisor import SYSTEM_PROMPT
from roboqc_agent.schemas import Action

SUPERVISOR_NAME = "supervisor"


def build_supervisor_agent(
    *,
    instruction: str = SYSTEM_PROMPT,
    model: str = "gemini-2.5-pro",
) -> Agent:
    """Build the Supervisor routing agent."""

    return Agent(
        name=SUPERVISOR_NAME,
        description="Routes inspected SMT tiles to pass, rework, hold, or human review.",
        model=model,
        instruction=instruction,
        output_schema=Action,
        include_contents="none",
    )


__all__ = ["SUPERVISOR_NAME", "build_supervisor_agent"]
