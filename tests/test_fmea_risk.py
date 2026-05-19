from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.fmea_risk import FMEA_RISK_NAME, build_fmea_risk_agent
from roboqc_agent.prompts.fmea_risk import SYSTEM_PROMPT
from roboqc_agent.schemas import FMEAEntry


def test_build_fmea_risk_agent_uses_prompt_constant() -> None:
    agent = build_fmea_risk_agent()

    assert isinstance(agent, Agent)
    assert agent.name == FMEA_RISK_NAME
    assert agent.model == "gemini-2.5-pro"
    assert agent.instruction == SYSTEM_PROMPT
    assert agent.output_schema == list[FMEAEntry]
    assert agent.include_contents == "none"
