"""Single Streamlit demo UI for RoboQC Agent.

One operator-facing surface (architecture §10): the four-agent decomposition is
invisible — the operator sees one "RoboQC" decision per tile, with confidence as
a color, and can drill into each agent's contribution and the evidence record.

Provider selection:
- ``GOOGLE_CLOUD_PROJECT`` set  -> live Vertex AI Gemini (real inference).
- otherwise                     -> offline ``DemoProvider`` (no GCP needed).

Run locally:  streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime

import streamlit as st

from roboqc_agent.agents.evidence_report import aggregate_board, summarize_board
from roboqc_agent.graph import InspectionProvider, RoboQCPipeline
from roboqc_agent.providers.demo import DemoProvider
from roboqc_agent.schemas import Action, ActionKind, TilePosition, TileReport

_ACTION_COLOR = {
    ActionKind.PASS: "🟢",
    ActionKind.REWORK: "🟡",
    ActionKind.HOLD: "🔴",
    ActionKind.HUMAN_REVIEW: "🟠",
}


def _build_provider() -> tuple[InspectionProvider, str]:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        from roboqc_agent.providers.vertex_gemini import VertexGeminiProvider

        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        return VertexGeminiProvider(project=project, location=location), f"Vertex AI ({project})"
    return DemoProvider(), "offline demo provider"


def _pipeline() -> RoboQCPipeline:
    if "pipeline" not in st.session_state:
        provider, label = _build_provider()
        st.session_state.pipeline = RoboQCPipeline(provider)
        st.session_state.provider_label = label
    return st.session_state.pipeline


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.95:
        return "🟢 high"
    if confidence >= 0.80:
        return "🟡 medium"
    return "🔴 low"


def _render_agent_breakdown(report: TileReport) -> None:
    """Show each of the four agents' contributions for one tile."""

    with st.expander("Agent breakdown (Vision → FMEA → Supervisor → Evidence)"):
        st.markdown("**1. Vision Inspector** — defect candidates")
        if report.defects:
            st.table(
                [
                    {
                        "class": d.defect_class.value,
                        "confidence": f"{d.confidence:.2f}",
                        "source": d.source,
                        "bbox": f"({d.bbox.x},{d.bbox.y},{d.bbox.w},{d.bbox.h})",
                    }
                    for d in report.defects
                ]
            )
        else:
            st.success("Clean tile — no defects detected.")

        st.markdown("**2. FMEA Risk** — severity & default action")
        if report.fmea_entries:
            st.table(
                [
                    {
                        "severity": e.severity.value,
                        "default_action": e.default_action.value,
                        "escalate": "yes" if e.escalate_to_senior else "no",
                        "justification": e.justification,
                    }
                    for e in report.fmea_entries
                ]
            )
        else:
            st.caption("No defects to risk-map.")

        action = report.agent_action
        st.markdown("**3. Supervisor** — final decision")
        st.write(f"{_ACTION_COLOR[action.kind]} **{action.kind.value.upper()}** — {action.reason}")
        st.caption(
            f"Aggregate confidence: {_confidence_band(action.confidence)} "
            f"({action.confidence:.2f}) · HITL triggered: {action.triggered_hitl}"
        )

        st.markdown("**4. Evidence Report** — audit record (JSON)")
        st.json(report.model_dump(mode="json"))


def _inspect_view() -> None:
    st.subheader("Tile capture & inspection")
    cfg = st.session_state.session_cfg

    col1, col2, col3 = st.columns(3)
    row = col1.number_input("Tile row", min_value=0, value=0, step=1)
    col = col2.number_input("Tile col", min_value=0, value=0, step=1)
    col3.metric("Tiles inspected", len(st.session_state.tile_reports))

    uploaded = st.file_uploader("Upload microscope tile image", type=["png", "jpg", "jpeg", "bmp"])
    if uploaded is not None:
        st.image(uploaded, caption="Captured tile", width=360)

    if st.button("Run RoboQC on tile", type="primary", disabled=uploaded is None):
        suffix = os.path.splitext(uploaded.name)[1] or ".png"  # type: ignore[union-attr]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(uploaded.getvalue())  # type: ignore[union-attr]
            image_path = tmp.name

        from roboqc_agent.schemas import Tile

        tile = Tile(
            board_id=cfg["board_id"],
            lot_id=cfg["lot_id"],
            position=TilePosition(row=int(row), col=int(col)),
            magnification=cfg["magnification"],
            image_uri=f"file://{image_path}",
            captured_at=datetime.now(UTC),
            operator_id=cfg["operator_id"],
        )
        with st.spinner(f"Running four-agent brigade via {st.session_state.provider_label}…"):
            report = _pipeline().inspect_tile(tile, image_path)
        st.session_state.tile_reports.append(report)
        st.session_state.last_report = report

    report = st.session_state.get("last_report")
    if report is not None:
        action: Action = report.agent_action
        st.markdown("---")
        badge = _ACTION_COLOR[action.kind]
        st.markdown(f"### {badge} RoboQC says: **{action.kind.value.upper()}**")
        st.write(action.reason)
        if action.triggered_hitl:
            st.warning("Human-in-the-loop gate triggered — operator decision required.")
        _render_agent_breakdown(report)


def _rollup_view() -> None:
    st.subheader("Board rollup")
    reports: list[TileReport] = st.session_state.tile_reports
    if not reports:
        st.info("Inspect at least one tile to see the board rollup.")
        return

    cfg = st.session_state.session_cfg
    qc_report = aggregate_board(
        board_id=cfg["board_id"],
        lot_id=cfg["lot_id"],
        operator_id=cfg["operator_id"],
        started_at=st.session_state.started_at,
        tile_reports=reports,
    )

    st.write(summarize_board(qc_report))

    c1, c2, c3 = st.columns(3)
    c1.metric("Tiles", len(qc_report.tile_reports))
    c2.metric("Board status", qc_report.status.value.upper())
    c3.metric("Senior escalations", len(qc_report.senior_escalations))

    if qc_report.defect_histogram:
        st.markdown("**Defect histogram**")
        st.bar_chart({cls.value: count for cls, count in qc_report.defect_histogram.items()})

    action_counts: dict[str, int] = {}
    for tr in reports:
        kind = tr.agent_action.kind.value
        action_counts[kind] = action_counts.get(kind, 0) + 1
    st.markdown("**Per-tile actions**")
    st.table([{"action": k, "tiles": v} for k, v in action_counts.items()])


def main() -> None:
    st.set_page_config(page_title="RoboQC Agent", page_icon="🔬", layout="wide")
    st.title("🔬 RoboQC Agent — SMT first-article inspection")
    _pipeline()
    st.caption(f"Inference backend: {st.session_state.provider_label}")

    if "tile_reports" not in st.session_state:
        st.session_state.tile_reports = []
        st.session_state.started_at = datetime.now(UTC)

    with st.sidebar:
        st.header("Session setup")
        board_id = st.text_input("Board model / ID", value="BRD-DEMO-001")
        lot_id = st.text_input("Lot ID", value="LOT-2026-001")
        operator_id = st.text_input("Operator ID", value="op-demo")
        magnification = st.selectbox("Magnification", options=[5, 10, 20, 40], index=1)
        st.session_state.session_cfg = {
            "board_id": board_id,
            "lot_id": lot_id,
            "operator_id": operator_id,
            "magnification": magnification,
        }
        if st.button("Reset session"):
            st.session_state.tile_reports = []
            st.session_state.pop("last_report", None)
            st.session_state.started_at = datetime.now(UTC)
            st.rerun()

    inspect_tab, rollup_tab = st.tabs(["Inspect tile", "Board rollup"])
    with inspect_tab:
        _inspect_view()
    with rollup_tab:
        _rollup_view()


if __name__ == "__main__":
    main()
