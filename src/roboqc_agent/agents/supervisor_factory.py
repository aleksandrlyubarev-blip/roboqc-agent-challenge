"""ADK factory for the Supervisor agent."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from roboqc_agent.config import default_model
from roboqc_agent.prompts.supervisor import SYSTEM_PROMPT
from roboqc_agent.schemas import Action

SUPERVISOR_NAME = "supervisor"
SUPERVISOR_STATE_KEY = "action"


def build_supervisor_agent(
    *,
    instruction: str = SYSTEM_PROMPT,
    model: str | None = None,
) -> Agent:
    """Build the Supervisor routing agent.

    The LLM proposes the routing decision; the deterministic
    ``FrictionPolicyEngine`` (see ``orchestration.board_flow``) remains the
    enforcement layer that validates or overrides it.
    """

    return Agent(
        name=SUPERVISOR_NAME,
        description="Routes inspected SMT tiles to pass, rework, hold, or human review.",
        model=model or default_model(),
        instruction=instruction,
        output_schema=Action,
        output_key=SUPERVISOR_STATE_KEY,
        include_contents="none",
    )


__all__ = ["SUPERVISOR_NAME", "SUPERVISOR_STATE_KEY", "build_supervisor_agent"]
