from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.fmea_risk import FMEA_RISK_NAME, build_fmea_risk_agent
from roboqc_agent.schemas import FMEAEntry


def test_build_fmea_risk_agent_keeps_prompt_injected() -> None:
    agent = build_fmea_risk_agent(instruction="map defects to FMEA entries")

    assert isinstance(agent, Agent)
    assert agent.name == FMEA_RISK_NAME
    assert agent.model == "gemini-2.5-pro"
    assert agent.instruction == "map defects to FMEA entries"
    assert agent.output_schema == list[FMEAEntry]
    assert agent.include_contents == "none"
