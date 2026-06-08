"""ADK graph skeleton for the RoboQC workflow."""

from __future__ import annotations

from dataclasses import dataclass

from google.adk.agents import SequentialAgent
from google.adk.agents.llm_agent import Agent

from roboqc_agent.agents.evidence_report_factory import build_evidence_report_agent
from roboqc_agent.agents.fmea_risk import build_fmea_risk_agent
from roboqc_agent.agents.supervisor_factory import build_supervisor_agent
from roboqc_agent.agents.vision_inspector import build_vision_inspector_agent


@dataclass(frozen=True, slots=True)
class RoboQCGraphSkeleton:
    """Current graph shape before full runtime invocation is implemented."""

    tile_flow: SequentialAgent
    evidence_report_agent: Agent


def build_roboqc_graph_skeleton(
    *,
    model: str = "gemini-2.5-pro",
) -> RoboQCGraphSkeleton:
    """Build the approved four-agent ADK skeleton.

    Per-tile chain:
        Vision Inspector → FMEA Risk → Supervisor

    Board-finalization chain:
        Evidence Report runs after all tiles are complete.
    """

    # Issue #21 resolved: the Vision Inspector prompt now emits Defect-shaped
    # objects (defect_class / bbox{x,y,w,h} / source) matching the frozen schema,
    # so the skeleton builds without the schema-mismatch escape hatch.
    vision_inspector = build_vision_inspector_agent(model=model)
    fmea_risk = build_fmea_risk_agent(model=model)
    supervisor = build_supervisor_agent(model=model)
    evidence_report = build_evidence_report_agent(model=model)

    tile_flow = SequentialAgent(
        name="roboqc_tile_flow",
        description="Per-tile SMT inspection flow: vision, FMEA risk, supervisor routing.",
        sub_agents=[vision_inspector, fmea_risk, supervisor],
    )

    # TODO: Wire runtime state keys once prompt/schema mismatch is resolved in
    # GitHub issue #21.
    # TODO: Invoke evidence_report only after the UI / API marks all expected
    # tiles complete for a board.
    # TODO: Persist TileReport / QCReport through execution_store after each
    # finalized tile and board aggregation.
    return RoboQCGraphSkeleton(
        tile_flow=tile_flow,
        evidence_report_agent=evidence_report,
    )


__all__ = ["RoboQCGraphSkeleton", "build_roboqc_graph_skeleton"]
