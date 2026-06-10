from google.adk.workflow import Workflow

from roboqc_agent.graph import RoboQCGraphSkeleton, build_roboqc_graph_skeleton


def test_build_roboqc_graph_skeleton_orders_tile_flow_agents() -> None:
    graph = build_roboqc_graph_skeleton()

    assert isinstance(graph, RoboQCGraphSkeleton)
    assert isinstance(graph.tile_flow, Workflow)
    assert graph.tile_flow.graph is not None
    assert [node.name for node in graph.tile_flow.graph.nodes] == [
        "__START__",
        "vision_inspector",
        "fmea_risk",
        "supervisor",
    ]
    assert graph.evidence_report_agent.name == "evidence_report"


def test_agents_write_outputs_to_stable_state_keys() -> None:
    graph = build_roboqc_graph_skeleton()
    agents = {node.name: node for node in graph.tile_flow.graph.nodes if node.name != "__START__"}

    assert agents["vision_inspector"].output_key == "defects"
    assert agents["fmea_risk"].output_key == "fmea_entries"
    assert agents["supervisor"].output_key == "action"
    assert graph.evidence_report_agent.output_key == "qc_report"


def test_model_override_via_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ROBOQC_MODEL", "gemini-x-test")
    graph = build_roboqc_graph_skeleton()
    assert graph.evidence_report_agent.model == "gemini-x-test"

    explicit = build_roboqc_graph_skeleton(model="gemini-explicit")
    assert explicit.evidence_report_agent.model == "gemini-explicit"
