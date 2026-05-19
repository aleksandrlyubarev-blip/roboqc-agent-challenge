from google.adk.agents import SequentialAgent

from roboqc_agent.graph import RoboQCGraphSkeleton, build_roboqc_graph_skeleton


def test_build_roboqc_graph_skeleton_orders_tile_flow_agents() -> None:
    graph = build_roboqc_graph_skeleton()

    assert isinstance(graph, RoboQCGraphSkeleton)
    assert isinstance(graph.tile_flow, SequentialAgent)
    assert [agent.name for agent in graph.tile_flow.sub_agents] == [
        "vision_inspector",
        "fmea_risk",
        "supervisor",
    ]
    assert graph.evidence_report_agent.name == "evidence_report"
