"""
Neuron Vision Display — Streamlit UI
System: RomeoFlexVision | Google ADK + Vertex AI Gemini 2.5 Pro

Production-ready PCB visual QC dashboard.
"""
from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# ── Bootstrap ────────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Demo mode — enabled by env var or when no GCP project is configured
_DEMO_MODE_DEFAULT = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes") \
    or not os.environ.get("GOOGLE_CLOUD_PROJECT", "")

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Neuron Vision Display — RomeoFlexVision",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Brand palette ─────────────────────────────────────── */
:root {
    --rv-blue:   #1565C0;
    --rv-green:  #2E7D32;
    --rv-amber:  #F57F17;
    --rv-red:    #B71C1C;
    --rv-purple: #4A148C;
    --rv-grey:   #37474F;
}

/* ── Verdict badges ────────────────────────────────────── */
.verdict-pass         { background:#2E7D32; color:#fff; padding:12px 28px;
                        border-radius:8px; font-size:1.6rem; font-weight:700;
                        display:inline-block; margin:8px 0; letter-spacing:2px; }
.verdict-rework       { background:#E65100; color:#fff; padding:12px 28px;
                        border-radius:8px; font-size:1.6rem; font-weight:700;
                        display:inline-block; margin:8px 0; letter-spacing:2px; }
.verdict-hold         { background:#F57F17; color:#fff; padding:12px 28px;
                        border-radius:8px; font-size:1.6rem; font-weight:700;
                        display:inline-block; margin:8px 0; letter-spacing:2px; }
.verdict-human_review { background:#B71C1C; color:#fff; padding:12px 28px;
                        border-radius:8px; font-size:1.6rem; font-weight:700;
                        display:inline-block; margin:8px 0; letter-spacing:2px; }

/* ── Agent stage pill ──────────────────────────────────── */
.stage-active    { background:#1565C0; color:#fff; border-radius:20px;
                   padding:4px 14px; font-size:0.85rem; font-weight:600; }
.stage-complete  { background:#2E7D32; color:#fff; border-radius:20px;
                   padding:4px 14px; font-size:0.85rem; font-weight:600; }
.stage-pending   { background:#90A4AE; color:#fff; border-radius:20px;
                   padding:4px 14px; font-size:0.85rem; }

/* ── Evidence log ──────────────────────────────────────── */
.evidence-critical { border-left:4px solid #B71C1C; padding:6px 12px;
                     background:#FFEBEE; margin:4px 0; border-radius:0 6px 6px 0; }
.evidence-moderate { border-left:4px solid #E65100; padding:6px 12px;
                     background:#FFF3E0; margin:4px 0; border-radius:0 6px 6px 0; }
.evidence-minor    { border-left:4px solid #F9A825; padding:6px 12px;
                     background:#FFFDE7; margin:4px 0; border-radius:0 6px 6px 0; }
.evidence-info     { border-left:4px solid #1565C0; padding:6px 12px;
                     background:#E3F2FD; margin:4px 0; border-radius:0 6px 6px 0; }

.metric-box { background:#F5F5F5; border-radius:8px; padding:12px;
              text-align:center; border:1px solid #E0E0E0; }
.metric-value { font-size:1.8rem; font-weight:700; color:#1565C0; }
.metric-label { font-size:0.8rem; color:#607D8B; margin-top:2px; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Google_Cloud_logo.svg/200px-Google_Cloud_logo.svg.png",
        width=140,
    )
    st.markdown("## 🔬 Neuron Vision Display")
    st.markdown("**System:** RomeoFlexVision  \n**Model:** Gemini 2.5 Pro  \n**Region:** us-central1")
    st.divider()

    st.markdown("### ⚙️ Configuration")

    demo_mode = st.toggle(
        "🎭 Demo Mode",
        value=_DEMO_MODE_DEFAULT,
        help="Run without Vertex AI — uses pre-built realistic scenarios",
    )

    if not demo_mode:
        project_id = st.text_input(
            "GCP Project ID",
            value=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
            help="Your Google Cloud project ID",
        )
        if project_id:
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    else:
        demo_scenario = st.selectbox(
            "Demo scenario",
            options=["auto (from image hash)", "pass", "rework", "human_review"],
            help="Force a specific QC outcome for the demo",
        )

    st.divider()

    # Example images from examples/ folder
    examples_dir = Path("examples/pcb_samples")
    example_files = sorted(examples_dir.glob("*.jpg")) + sorted(examples_dir.glob("*.png")) if examples_dir.exists() else []

    if example_files:
        st.markdown("### 📂 Sample Images")
        selected_example = st.selectbox(
            "Load a sample PCB",
            options=["— select —"] + [f.name for f in example_files],
        )
    else:
        selected_example = "— select —"

    st.divider()
    st.markdown(
        "<small>© 2026 RomeoFlexVision · "
        "[Google for Startups AI Agents Challenge](https://devpost.com)</small>",
        unsafe_allow_html=True,
    )

# ── Main header ───────────────────────────────────────────────────────────────
st.markdown("# 🔬 Neuron Vision Display")
st.markdown(
    "**Multi-agent visual QC for SMT PCB manufacturing** — "
    "_powered by Google ADK + Gemini 2.5 Pro_"
)
st.divider()

# ── Image input ───────────────────────────────────────────────────────────────
col_upload, col_preview = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown("### 📷 Load PCB Image")

    uploaded = st.file_uploader(
        "Upload a PCB photo",
        type=["jpg", "jpeg", "png"],
        help="High-resolution top-down photo works best. Minimum 800×600 px recommended.",
    )

    image_bytes: Optional[bytes] = None
    image_source = None

    if uploaded is not None:
        image_bytes = uploaded.read()
        image_source = uploaded.name
    elif selected_example and selected_example != "— select —":
        example_path = examples_dir / selected_example
        if example_path.exists():
            image_bytes = example_path.read_bytes()
            image_source = selected_example

with col_preview:
    if image_bytes:
        st.markdown("### 🖼️ Preview")
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            st.image(pil_img, caption=image_source, use_container_width=True)
            w, h = pil_img.size
            st.caption(f"{w}×{h} px · {len(image_bytes) / 1024:.0f} KB")
        except Exception as e:
            st.error(f"Cannot display image: {e}")

# ── Run button ────────────────────────────────────────────────────────────────
st.divider()

run_col, spacer = st.columns([2, 5])
with run_col:
    run_disabled = image_bytes is None
    run_clicked = st.button(
        "▶️ Run QC Inspection",
        type="primary",
        disabled=run_disabled,
        use_container_width=True,
    )
    if image_bytes is None:
        st.caption("⬆️ Upload an image to enable inspection")
    elif demo_mode:
        st.caption("🎭 Demo mode active — no GCP required")
    elif not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        st.caption("⚙️ Set GCP Project ID in the sidebar")

# ── Inspection execution ──────────────────────────────────────────────────────
if run_clicked and image_bytes:
    # ── Demo Mode banner ───────────────────────────────────────────────────
    if demo_mode:
        st.warning(
            "⚡ **Running in Demo Mode** — results are simulated with realistic scenarios. "
            "Disable Demo Mode in the sidebar and set a GCP Project ID to run live inference.",
            icon="🎭",
        )

    # ── Load pipeline ──────────────────────────────────────────────────────
    if demo_mode:
        try:
            from src.neuron_vision.demo_mode import DemoPipeline
            _forced = None if demo_scenario == "auto (from image hash)" else demo_scenario
            pipeline = DemoPipeline(scenario=_forced, speed=0.6)
        except ImportError as e:
            st.error(f"❌ Demo mode import error: {e}")
            st.stop()
    else:
        try:
            from src.neuron_vision.pipeline import NeuronVisionPipeline
            pipeline = NeuronVisionPipeline()
        except ImportError as e:
            st.error(f"❌ Import error: {e}. Ensure you're running from the repo root with all dependencies installed.")
            st.stop()

    st.divider()
    st.markdown("## 🤖 Agent Brigade — Live Progress")

    # ── Stage progress display ─────────────────────────────────────────────
    STAGES = [
        ("triage",     "🔍 Triage Agent",            "Stage 1: Board type & risk zones"),
        ("solder",     "🔧 Solder Inspector",         "Stage 2a: Joint quality"),
        ("components", "🧩 Component Inspector",      "Stage 2b: Placement & presence"),
        ("markings",   "🏷️ Marking Inspector",        "Stage 2c: Silkscreen & QR"),
        ("chief",      "🎯 Chief Inspector",          "Stage 3: Verdict & evidence"),
    ]

    stage_cols = st.columns(len(STAGES))
    stage_placeholders = {}
    for i, (key, label, desc) in enumerate(STAGES):
        with stage_cols[i]:
            stage_placeholders[key] = st.empty()
            stage_placeholders[key].markdown(
                f'<div class="stage-pending">{label}</div><br><small>{desc}</small>',
                unsafe_allow_html=True,
            )

    completed_stages: list[str] = []
    current_stage_key: list[str] = []  # mutable container for closure

    progress_bar = st.progress(0, text="Initialising pipeline …")
    status_text = st.empty()

    def on_stage(stage_name: str) -> None:
        """Callback invoked by the pipeline after each stage completes."""
        completed_stages.append(stage_name)
        n_complete = len(completed_stages)

        for i, (key, label, desc) in enumerate(STAGES):
            if key in completed_stages:
                stage_placeholders[key].markdown(
                    f'<div class="stage-complete">✅ {label}</div><br><small>{desc}</small>',
                    unsafe_allow_html=True,
                )
            elif key == stage_name:
                stage_placeholders[key].markdown(
                    f'<div class="stage-active">⏳ {label}</div><br><small>{desc}</small>',
                    unsafe_allow_html=True,
                )

        pct = int(n_complete / len(STAGES) * 100)
        progress_bar.progress(pct, text=f"Completed: {', '.join(completed_stages)}")
        status_text.markdown(f"✅ **{label}** completed")

    # Mark triage as active immediately
    stage_placeholders["triage"].markdown(
        f'<div class="stage-active">⏳ 🔍 Triage Agent</div><br><small>Stage 1: Board type & risk zones</small>',
        unsafe_allow_html=True,
    )

    t0 = time.perf_counter()

    with st.spinner("Running 5-agent QC brigade …"):
        try:
            result = pipeline.run(image_bytes, on_stage=on_stage)
        except Exception as exc:
            st.error(f"❌ Pipeline error: {exc}")
            st.exception(exc)
            st.stop()

    elapsed = time.perf_counter() - t0
    progress_bar.progress(100, text="Inspection complete")
    status_text.markdown(f"**All 5 agents completed in {elapsed:.1f}s**")

    # ── Verdict display ────────────────────────────────────────────────────
    st.divider()
    st.markdown("## 📋 QC Verdict")

    verdict = result.verdict
    status = verdict.status

    VERDICT_ICONS = {
        "pass":         "✅",
        "rework":       "🔧",
        "hold":         "⏸️",
        "human_review": "👁️",
    }
    VERDICT_LABELS = {
        "pass":         "PASS — Clear to ship",
        "rework":       "REWORK — Defects found",
        "hold":         "HOLD — Manual review needed",
        "human_review": "HUMAN REVIEW — Escalate now",
    }

    icon = VERDICT_ICONS.get(status, "❓")
    label = VERDICT_LABELS.get(status, status.upper())

    # ── Verdict badge (centred) ────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;padding:16px 0">'
        f'<div class="verdict-{status}" style="font-size:2rem;padding:18px 48px">'
        f'{icon} {label}</div>'
        f'<p style="margin-top:12px;font-size:1.1rem;color:#37474F">{verdict.summary}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Metrics row ────────────────────────────────────────────────────────
    total_defects = len(result.solder.defects) + len(result.components.issues) + len(result.markings.issues)
    critical_count = sum(
        1 for e in verdict.evidence_log if e.severity == "critical"
    )
    conf_pct = int(verdict.confidence * 100)

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{total_defects}</div>'
            f'<div class="metric-label">Total findings</div></div>',
            unsafe_allow_html=True,
        )
    with mc2:
        color = "#B71C1C" if critical_count > 0 else "#2E7D32"
        st.markdown(
            f'<div class="metric-box"><div class="metric-value" style="color:{color}">'
            f'{critical_count}</div>'
            f'<div class="metric-label">Critical</div></div>',
            unsafe_allow_html=True,
        )
    with mc3:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{result.duration_seconds:.1f}s</div>'
            f'<div class="metric-label">Inspection time</div></div>',
            unsafe_allow_html=True,
        )
    with mc4:
        st.markdown(
            f'<div class="metric-box"><div class="metric-value">{conf_pct}%</div>'
            f'<div class="metric-label">Confidence</div></div>',
            unsafe_allow_html=True,
        )

    # ── Recommended actions ────────────────────────────────────────────────
    if verdict.recommended_actions:
        st.markdown("### 🛠️ Recommended Actions")
        for i, action in enumerate(verdict.recommended_actions, 1):
            st.markdown(f"{i}. {action}")

    # ── Evidence Log ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("## 📑 Evidence Log")

    if verdict.evidence_log:
        SEVERITY_ORDER = {"critical": 0, "moderate": 1, "minor": 2, "info": 3}
        SEVERITY_ICONS = {"critical": "🔴", "moderate": "🟠", "minor": "🟡", "info": "🔵"}
        sorted_evidence = sorted(
            verdict.evidence_log,
            key=lambda e: SEVERITY_ORDER.get(e.severity, 99),
        )
        for entry in sorted_evidence:
            agent_label = entry.source_agent.replace("_", " ").title()
            sev = entry.severity
            icon_sev = SEVERITY_ICONS.get(sev, "⚪")
            st.markdown(
                f'<div class="evidence-{sev}">'
                f'{icon_sev} <strong>[{agent_label}]</strong> <em>{sev.upper()}</em> — {entry.finding}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No findings recorded in the evidence log.")

    # ── Detailed reports in expanders ──────────────────────────────────────
    st.divider()
    st.markdown("## 🔎 Detailed Specialist Reports")

    with st.expander("🔍 Triage Agent — Board Assessment", expanded=False):
        t = result.triage
        st.markdown(f"**Board type:** {t.board_type}")
        st.markdown(f"**Inspection priority:** `{t.inspection_priority}`")
        st.markdown(f"**Confidence:** {t.confidence:.0%}")
        if t.risk_zones:
            st.markdown("**Risk zones identified:**")
            for z in t.risk_zones:
                st.markdown(f"  • {z}")
        if t.notes:
            st.markdown(f"**Notes:** {t.notes}")

    with st.expander(f"🔧 Solder Inspector — {len(result.solder.defects)} defect(s) found", expanded=False):
        s = result.solder
        st.markdown(f"**Overall solder quality:** `{s.overall_solder_quality}`")
        st.markdown(f"**Joints inspected (estimate):** {s.inspected_joints_estimate}")
        st.markdown(f"**Confidence:** {s.confidence:.0%}")
        st.markdown(f"**Summary:** {s.summary}")
        if s.defects:
            st.markdown("**Defects:**")
            for d in s.defects:
                sev_emoji = {"minor": "🟡", "moderate": "🟠", "critical": "🔴"}.get(d.severity, "⚪")
                st.markdown(
                    f"  {sev_emoji} `{d.defect_type}` at **{d.location}** "
                    f"— severity: {d.severity} ({d.confidence:.0%} confidence)"
                )

    with st.expander(f"🧩 Component Inspector — {len(result.components.issues)} issue(s) found", expanded=False):
        c = result.components
        st.markdown(f"**Overall placement quality:** `{c.overall_placement_quality}`")
        st.markdown(f"**Confidence:** {c.confidence:.0%}")
        st.markdown(f"**Summary:** {c.summary}")
        if c.missing:
            st.markdown(f"**Missing components:** {', '.join(c.missing)}")
        if c.misoriented:
            st.markdown(f"**Misoriented:** {', '.join(c.misoriented)}")
        if c.shifted:
            st.markdown(f"**Shifted:** {', '.join(c.shifted)}")
        if c.issues:
            st.markdown("**All issues:**")
            for issue in c.issues:
                sev_emoji = {"minor": "🟡", "moderate": "🟠", "critical": "🔴"}.get(issue.severity, "⚪")
                st.markdown(
                    f"  {sev_emoji} **{issue.component_ref}** — `{issue.issue_type}` "
                    f"({issue.severity})" + (f": {issue.details}" if issue.details else "")
                )

    with st.expander(f"🏷️ Marking Inspector — {len(result.markings.issues)} issue(s) found", expanded=False):
        m = result.markings
        st.markdown(f"**Overall marking quality:** `{m.overall_marking_quality}`")
        st.markdown(f"**QR/Barcode valid:** {'✅ Yes' if m.qr_valid else '❌ No'}")
        st.markdown(f"**Confidence:** {m.confidence:.0%}")
        st.markdown(f"**Summary:** {m.summary}")
        if m.unreadable:
            st.markdown(f"**Unreadable areas:** {', '.join(m.unreadable)}")
        if m.missing_marks:
            st.markdown(f"**Missing marks:** {', '.join(m.missing_marks)}")
        if m.issues:
            st.markdown("**All issues:**")
            for issue in m.issues:
                sev_emoji = {"minor": "🟡", "moderate": "🟠", "critical": "🔴"}.get(issue.severity, "⚪")
                st.markdown(
                    f"  {sev_emoji} **{issue.area}** — `{issue.issue_type}` ({issue.severity})"
                )

    # ── Performance stats + footer ─────────────────────────────────────────
    st.divider()
    mode_label = "🎭 Demo Mode" if demo_mode else "⚡ Gemini 2.5 Pro · us-central1"
    st.markdown(
        f"<small>⏱️ **{result.duration_seconds:.1f}s** · {mode_label} · "
        f"Powered by **Google ADK** + **Vertex AI** | RomeoFlexVision</small>",
        unsafe_allow_html=True,
    )

else:
    # ── Landing state ──────────────────────────────────────────────────────
    st.markdown("## How it works")
    cols = st.columns(5, gap="small")
    agent_cards = [
        ("🔍", "Triage Agent", "Identifies board type and maps high-risk inspection zones"),
        ("🔧", "Solder Inspector", "Detects cold joints, bridges, insufficient/excess solder"),
        ("🧩", "Component Inspector", "Checks placement, orientation, missing parts"),
        ("🏷️", "Marking Inspector", "Validates silkscreen, QR codes, polarity marks"),
        ("🎯", "Chief Inspector", "Synthesises all findings into a binding QC verdict"),
    ]
    for col, (icon, name, desc) in zip(cols, agent_cards):
        with col:
            st.markdown(
                f'<div class="metric-box" style="min-height:140px;">'
                f'<div style="font-size:2rem">{icon}</div>'
                f'<div style="font-weight:700;margin:8px 0 4px">{name}</div>'
                f'<div style="font-size:0.8rem;color:#607D8B">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown(
        """
        **Quick start:**
        1. Set your GCP Project ID in the sidebar (or add it to `.env`)
        2. Upload a PCB photo (JPEG/PNG) **or** select a sample from the sidebar
        3. Click **▶️ Run QC Inspection**
        4. The 5-agent brigade analyses your board in seconds

        > **Verdict codes:** ✅ PASS · 🔧 REWORK · ⏸️ HOLD · 👁️ HUMAN REVIEW
        """
    )
