from uuid import uuid4

from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.fmea_risk import (
    FMEA_RISK_NAME,
    FMEAObservation,
    build_fmea_risk_agent,
    to_fmea_entries,
)
from roboqc_agent.schemas import ActionKind, BBox, Defect, DefectClass, Severity


def test_build_fmea_risk_agent_keeps_prompt_injected() -> None:
    agent = build_fmea_risk_agent(instruction="map defects to FMEA entries")

    assert isinstance(agent, Agent)
    assert agent.name == FMEA_RISK_NAME
    assert agent.model == "gemini-2.5-pro"
    assert agent.instruction == "map defects to FMEA entries"
    assert agent.output_schema == list[FMEAObservation]
    assert agent.include_contents == "none"


def test_to_fmea_entries_links_observations_to_defects_by_order() -> None:
    tile_id = uuid4()
    defects = [
        Defect(
            tile_id=tile_id,
            defect_class=DefectClass.OPEN_TRACE,
            bbox=BBox(x=1, y=1, w=2, h=2),
            confidence=0.9,
            source="labeled_detector",
        ),
        Defect(
            tile_id=tile_id,
            defect_class=DefectClass.SPUR,
            bbox=BBox(x=5, y=5, w=2, h=2),
            confidence=0.9,
            source="labeled_detector",
        ),
    ]
    observations = [
        FMEAObservation(
            severity=Severity.CRITICAL,
            default_action=ActionKind.HOLD,
            justification="open trace breaks the net",
        ),
        FMEAObservation(
            severity=Severity.MINOR,
            default_action=ActionKind.PASS,
            justification="cosmetic spur",
        ),
    ]

    entries = to_fmea_entries(observations, defects)

    assert [e.defect_id for e in entries] == [defects[0].defect_id, defects[1].defect_id]
    assert entries[0].severity is Severity.CRITICAL
    assert entries[1].default_action is ActionKind.PASS
