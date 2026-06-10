"""ADK graph for the RoboQC workflow."""

from __future__ import annotations

from dataclasses import dataclass

from google.adk.agents.llm_agent import Agent
from google.adk.workflow import START, Edge, Workflow

from roboqc_agent.agents.evidence_report_factory import build_evidence_report_agent
from roboqc_agent.agents.fmea_risk import build_fmea_risk_agent
from roboqc_agent.agents.supervisor_factory import build_supervisor_agent
from roboqc_agent.agents.vision_inspector import build_vision_inspector_agent


@dataclass(frozen=True, slots=True)
class RoboQCGraphSkeleton:
    """Tile-flow workflow plus the board-level evidence agent."""

    tile_flow: Workflow
    evidence_report_agent: Agent


def build_roboqc_graph_skeleton(
    *,
    model: str | None = None,
) -> RoboQCGraphSkeleton:
    """Build the approved four-agent ADK graph.

    Per-tile chain (Workflow, sequential edges):
        Vision Inspector → FMEA Risk → Supervisor

    Each agent writes its structured output into session state under a stable
    key (``defects`` / ``fmea_entries`` / ``action``), so downstream consumers
    read state instead of parsing transcripts.

    Board finalization is owned by ``orchestration.board_flow``: the
    ``BoardFlowCoordinator`` persists every finalized tile through the
    execution store, enforces the deterministic friction policy over the
    Supervisor's proposal, and assembles the QCReport (with its recomputed
    defect histogram) only after all expected tiles are recorded. The
    ``evidence_report_agent`` remains available for narrative report
    generation on top of that deterministic aggregate.
    """

    vision_inspector = build_vision_inspector_agent(model=model)
    fmea_risk = build_fmea_risk_agent(model=model)
    supervisor = build_supervisor_agent(model=model)
    evidence_report = build_evidence_report_agent(model=model)

    tile_flow = Workflow(
        name="roboqc_tile_flow",
        description="Per-tile SMT inspection flow: vision, FMEA risk, supervisor routing.",
        edges=[
            Edge(from_node=START, to_node=vision_inspector),
            Edge(from_node=vision_inspector, to_node=fmea_risk),
            Edge(from_node=fmea_risk, to_node=supervisor),
        ],
    )

    return RoboQCGraphSkeleton(
        tile_flow=tile_flow,
        evidence_report_agent=evidence_report,
    )


__all__ = ["RoboQCGraphSkeleton", "build_roboqc_graph_skeleton"]
