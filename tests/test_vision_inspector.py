from uuid import uuid4

from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.vision_inspector import (
    VISION_INSPECTOR_NAME,
    DefectObservation,
    build_vision_inspector_agent,
    to_defects,
)
from roboqc_agent.schemas import BBox, DefectClass


def test_build_vision_inspector_agent_keeps_prompt_injected() -> None:
    agent = build_vision_inspector_agent(instruction="inspect one tile")

    assert isinstance(agent, Agent)
    assert agent.name == VISION_INSPECTOR_NAME
    assert agent.model == "gemini-2.5-pro"
    assert agent.instruction == "inspect one tile"
    assert agent.output_schema == list[DefectObservation]
    assert agent.include_contents == "none"


def test_to_defects_drops_below_floor_and_links_tile() -> None:
    tile_id = uuid4()
    observations = [
        DefectObservation(
            defect_class=DefectClass.OPEN_TRACE,
            bbox=BBox(x=10, y=10, w=4, h=4),
            confidence=0.92,
            source="labeled_detector",
        ),
        DefectObservation(
            defect_class=DefectClass.SPUR,
            bbox=BBox(x=200, y=200, w=4, h=4),
            confidence=0.30,  # below floor, dropped
            source="labeled_detector",
        ),
    ]

    defects = to_defects(observations, tile_id)

    assert len(defects) == 1
    assert defects[0].tile_id == tile_id
    assert defects[0].defect_class is DefectClass.OPEN_TRACE


def test_to_defects_deduplicates_same_class_in_one_region() -> None:
    tile_id = uuid4()
    observations = [
        DefectObservation(
            defect_class=DefectClass.SOLDER_BRIDGE,
            bbox=BBox(x=10, y=10, w=4, h=4),
            confidence=0.70,
            source="anomaly_arm",
        ),
        DefectObservation(
            defect_class=DefectClass.SOLDER_BRIDGE,
            bbox=BBox(x=12, y=12, w=4, h=4),  # same coarse bucket
            confidence=0.95,
            source="anomaly_arm",
        ),
    ]

    defects = to_defects(observations, tile_id)

    assert len(defects) == 1
    # Highest-confidence detection survives deduplication.
    assert defects[0].confidence == 0.95
