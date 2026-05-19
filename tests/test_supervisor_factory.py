from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.supervisor_factory import SUPERVISOR_NAME, build_supervisor_agent
from roboqc_agent.prompts.supervisor import SYSTEM_PROMPT
from roboqc_agent.schemas import Action


def test_build_supervisor_agent_uses_prompt_constant() -> None:
    agent = build_supervisor_agent()

    assert isinstance(agent, Agent)
    assert agent.name == SUPERVISOR_NAME
    assert agent.instruction == SYSTEM_PROMPT
    assert agent.output_schema is Action
    assert agent.include_contents == "none"
