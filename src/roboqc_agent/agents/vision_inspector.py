"""ADK factory for the Vision Inspector agent."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from roboqc_agent.prompts.vision_inspector import SYSTEM_PROMPT
from roboqc_agent.schemas import Defect

VISION_INSPECTOR_NAME = "vision_inspector"


def build_vision_inspector_agent(
    *,
    instruction: str = SYSTEM_PROMPT,
    model: str = "gemini-2.5-pro",
) -> Agent:
    """Build the multimodal Vision Inspector."""

    return Agent(
        name=VISION_INSPECTOR_NAME,
        description="Inspects one SMT microscope tile and emits defect candidates.",
        model=model,
        instruction=instruction,
        output_schema=list[Defect],
        include_contents="none",
    )


__all__ = ["VISION_INSPECTOR_NAME", "build_vision_inspector_agent"]
