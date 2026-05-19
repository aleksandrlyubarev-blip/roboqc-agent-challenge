from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.vision_inspector import (
    VISION_INSPECTOR_NAME,
    build_vision_inspector_agent,
)
from roboqc_agent.prompts.vision_inspector import SYSTEM_PROMPT
from roboqc_agent.schemas import Defect


def test_build_vision_inspector_agent_uses_prompt_constant() -> None:
    agent = build_vision_inspector_agent()

    assert isinstance(agent, Agent)
    assert agent.name == VISION_INSPECTOR_NAME
    assert agent.model == "gemini-2.5-pro"
    assert agent.instruction == SYSTEM_PROMPT
    assert agent.output_schema == list[Defect]
    assert agent.include_contents == "none"
