"""
Demo / Mock Mode for Neuron Vision Display.

Drop-in replacement for :class:`NeuronVisionPipeline` that returns realistic,
fully-typed :class:`PipelineResult` objects **without** any Vertex AI / Gemini
calls.  This keeps the hackathon demo alive on machines that have no GCP project,
no credentials, or no network access.

Enable it with the env-var ``DEMO_MODE=true`` or the sidebar toggle in ``app.py``.

Usage::

    pipeline = DemoPipeline()
    result = pipeline.run(image_bytes, on_stage=callback)

The public surface (``run`` / ``run_async`` signatures + return type) is identical
to :class:`NeuronVisionPipeline`, so it can be swapped in transparently.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from typing import Callable

from .schemas import (
    ComponentIssue,
    ComponentReport,
    EvidenceEntry,
    MarkingIssue,
    MarkingReport,
    PipelineResult,
    QCVerdict,
    SolderDefect,
    SolderReport,
    TriageResult,
)

logger = logging.getLogger(__name__)

# Per-stage simulated latency (seconds).  Roughly mimics a real Gemini round-trip
# while staying snappy enough for a live demo (~6-7s total across 5 stages).
_STAGE_DELAY = (0.8, 1.4)  # (min, max) — deterministic value derived from seed


def is_demo_mode() -> bool:
    """True when DEMO_MODE env-var is set to a truthy value."""
    return os.environ.get("DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Scenario builders — each returns a fully-populated PipelineResult (minus the
# duration, which the pipeline stamps after running).
# ---------------------------------------------------------------------------

def _scenario_pass() -> PipelineResult:
    """Scenario 1 — clean board, single minor cosmetic solder note. → PASS."""
    triage = TriageResult(
        board_type="double-layer SMT, 0.8 mm pitch",
        risk_zones=["U3 fine-pitch QFP", "J1 board-edge connector", "C-array decoupling bank"],
        inspection_priority="medium",
        confidence=0.94,
        notes="Reflow profile looks consistent. No obvious panel-level anomalies.",
    )
    solder = SolderReport(
        defects=[
            SolderDefect(
                defect_type="excess_solder",
                location="R12 pad B",
                severity="minor",
                confidence=0.71,
            ),
        ],
        overall_solder_quality="acceptable",
        inspected_joints_estimate=248,
        confidence=0.92,
        summary=(
            "All joints within IPC-A-610 Class 2 limits. One cosmetic excess-solder "
            "fillet at R12 — no electrical risk, no rework required."
        ),
    )
    components = ComponentReport(
        issues=[],
        missing=[],
        misoriented=[],
        shifted=[],
        overall_placement_quality="acceptable",
        confidence=0.96,
        summary="All 84 placed components present and within placement tolerance.",
    )
    markings = MarkingReport(
        issues=[],
        unreadable=[],
        missing_marks=[],
        qr_valid=True,
        overall_marking_quality="acceptable",
        confidence=0.95,
        summary="Silkscreen crisp, polarity marks present, QR/DataMatrix decodes cleanly.",
    )
    verdict = QCVerdict(
        status="pass",
        evidence_log=[
            EvidenceEntry(
                source_agent="triage",
                finding="Double-layer SMT board, reflow profile consistent across panel.",
                severity="info",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Minor cosmetic excess solder at R12 — within Class 2 tolerance.",
                severity="minor",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="All 84 components present and correctly placed.",
                severity="info",
            ),
            EvidenceEntry(
                source_agent="marking_inspector",
                finding="QR/DataMatrix valid; silkscreen and polarity marks legible.",
                severity="info",
            ),
        ],
        critical_findings=[],
        confidence=0.93,
        summary="Board passes QC. One cosmetic solder note logged; cleared to ship.",
        recommended_actions=[
            "Release board to next assembly stage.",
            "Log R12 cosmetic fillet for SPC trend monitoring (no action required).",
        ],
    )
    return PipelineResult(
        triage=triage,
        solder=solder,
        components=components,
        markings=markings,
        verdict=verdict,
        duration_seconds=0.0,
    )


def _scenario_rework() -> PipelineResult:
    """Scenario 2 — 2 moderate solder defects + 1 shifted component. → REWORK."""
    triage = TriageResult(
        board_type="double-layer SMT, mixed 0.5/0.8 mm pitch",
        risk_zones=["U4 QFN underside", "C7/C8 decoupling pair", "L2 inductor footprint"],
        inspection_priority="high",
        confidence=0.91,
        notes="Localised reflow inconsistency near U4 — flagged for solder specialist.",
    )
    solder = SolderReport(
        defects=[
            SolderDefect(
                defect_type="cold_joint",
                location="U4 pin 7",
                severity="moderate",
                confidence=0.84,
            ),
            SolderDefect(
                defect_type="insufficient_solder",
                location="C8 pad A",
                severity="moderate",
                confidence=0.79,
            ),
            SolderDefect(
                defect_type="excess_solder",
                location="R23 pad B",
                severity="minor",
                confidence=0.68,
            ),
        ],
        overall_solder_quality="marginal",
        inspected_joints_estimate=312,
        confidence=0.86,
        summary=(
            "Two reworkable solder defects detected: cold joint at U4.7 and "
            "insufficient solder at C8. Both addressable with localised touch-up."
        ),
    )
    components = ComponentReport(
        issues=[
            ComponentIssue(
                component_ref="C12",
                issue_type="shifted",
                severity="moderate",
                confidence=0.82,
                details="~0.35 mm X-offset, exceeds 0.25 mm placement tolerance.",
            ),
        ],
        missing=[],
        misoriented=[],
        shifted=["C12"],
        overall_placement_quality="marginal",
        confidence=0.88,
        summary="C12 placement shift beyond tolerance; remaining components nominal.",
    )
    markings = MarkingReport(
        issues=[],
        unreadable=[],
        missing_marks=[],
        qr_valid=True,
        overall_marking_quality="acceptable",
        confidence=0.93,
        summary="Markings legible, QR decodes. No labeling defects.",
    )
    verdict = QCVerdict(
        status="rework",
        evidence_log=[
            EvidenceEntry(
                source_agent="triage",
                finding="Localised reflow inconsistency near U4 flagged as high priority.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Cold joint at U4 pin 7 — reworkable, moderate severity.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Insufficient solder at C8 pad A — add solder, moderate severity.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="C12 shifted ~0.35 mm beyond placement tolerance.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="marking_inspector",
                finding="All markings legible; QR valid.",
                severity="info",
            ),
        ],
        critical_findings=[],
        confidence=0.85,
        summary=(
            "Board requires rework: 2 solder defects (U4.7 cold joint, C8 "
            "insufficient solder) and 1 component shift (C12). All reworkable."
        ),
        recommended_actions=[
            "Touch up cold joint at U4 pin 7 with controlled reflow.",
            "Add solder to C8 pad A and re-inspect fillet geometry.",
            "Re-seat C12 within placement tolerance.",
            "Re-run QC after rework to confirm pass.",
        ],
    )
    return PipelineResult(
        triage=triage,
        solder=solder,
        components=components,
        markings=markings,
        verdict=verdict,
        duration_seconds=0.0,
    )


def _scenario_human_review() -> PipelineResult:
    """Scenario 3 — critical bridge + missing component + illegible QR. → HUMAN_REVIEW."""
    triage = TriageResult(
        board_type="double-layer SMT, high-density 0.4 mm pitch",
        risk_zones=["U3 BGA cluster", "U7 fine-pitch QFN", "J1 power connector", "QR label zone"],
        inspection_priority="critical",
        confidence=0.89,
        notes="Multiple high-severity anomalies suspected — escalating to full brigade.",
    )
    solder = SolderReport(
        defects=[
            SolderDefect(
                defect_type="solder_bridge",
                location="U7 pins 14-15",
                severity="critical",
                confidence=0.93,
            ),
            SolderDefect(
                defect_type="cold_joint",
                location="U3 ball E4",
                severity="moderate",
                confidence=0.74,
            ),
        ],
        overall_solder_quality="reject",
        inspected_joints_estimate=486,
        confidence=0.9,
        summary=(
            "Critical solder bridge shorting U7 pins 14-15 — potential short circuit. "
            "Suspected cold joint under BGA U3 ball E4 requires X-ray confirmation."
        ),
    )
    components = ComponentReport(
        issues=[
            ComponentIssue(
                component_ref="R8",
                issue_type="missing",
                severity="critical",
                confidence=0.95,
                details="Pads bare, no component or solder present. Confirmed missing.",
            ),
            ComponentIssue(
                component_ref="D2",
                issue_type="misoriented",
                severity="moderate",
                confidence=0.81,
                details="Cathode band orientation reversed relative to silkscreen.",
            ),
        ],
        missing=["R8"],
        misoriented=["D2"],
        shifted=[],
        overall_placement_quality="reject",
        confidence=0.91,
        summary="R8 missing entirely; D2 reverse-mounted. Board not functional as-is.",
    )
    markings = MarkingReport(
        issues=[
            MarkingIssue(
                area="QR / DataMatrix label",
                issue_type="qr_unreadable",
                severity="critical",
                confidence=0.88,
            ),
            MarkingIssue(
                area="U3 reference designator",
                issue_type="illegible",
                severity="minor",
                confidence=0.7,
            ),
        ],
        unreadable=["QR/DataMatrix label", "U3 silkscreen"],
        missing_marks=[],
        qr_valid=False,
        overall_marking_quality="reject",
        confidence=0.87,
        summary=(
            "QR/DataMatrix unreadable — traceability broken. U3 designator partly "
            "obscured. Board cannot be tracked through MES."
        ),
    )
    verdict = QCVerdict(
        status="human_review",
        evidence_log=[
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Critical solder bridge shorting U7 pins 14-15 — short-circuit risk.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="R8 confirmed missing — bare pads, no solder.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="marking_inspector",
                finding="QR/DataMatrix label unreadable — traceability broken.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="D2 reverse-mounted (cathode band flipped).",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Suspected cold joint under BGA U3 ball E4 — needs X-ray.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="triage",
                finding="Multiple high-severity anomalies — escalated to full brigade.",
                severity="critical",
            ),
        ],
        critical_findings=[
            "Solder bridge U7 pins 14-15 (short-circuit risk)",
            "Component R8 missing",
            "QR/DataMatrix unreadable (traceability loss)",
        ],
        confidence=0.9,
        summary=(
            "Board escalated to HUMAN REVIEW: critical solder bridge at U7, missing "
            "R8, and unreadable QR. Combined severity exceeds auto-disposition policy."
        ),
        recommended_actions=[
            "Quarantine board — do not advance in line.",
            "Escalate to senior QC engineer for manual disposition.",
            "X-ray U3 BGA to confirm suspected cold joint at ball E4.",
            "Investigate feeder for R8 (possible pick-and-place miss).",
            "Re-print/re-apply QR label to restore MES traceability.",
        ],
    )
    return PipelineResult(
        triage=triage,
        solder=solder,
        components=components,
        markings=markings,
        verdict=verdict,
        duration_seconds=0.0,
    )


# Ordered list of (name, builder).  Index used for deterministic file-name routing.
_SCENARIOS: list[tuple[str, Callable[[], PipelineResult]]] = [
    ("pass", _scenario_pass),
    ("rework", _scenario_rework),
    ("human_review", _scenario_human_review),
]


def _select_scenario(image_bytes: bytes, filename: str | None) -> tuple[str, PipelineResult]:
    """
    Pick a scenario.

    Routing priority:
      1. Filename keyword hints (``pass`` / ``rework`` / ``review`` / ``fail``).
      2. Deterministic hash of (filename or image bytes) → stable across reruns
         of the *same* image, but varied across different images.
    """
    hint = (filename or "").lower()
    if any(k in hint for k in ("pass", "good", "ok", "clean")):
        idx = 0
    elif any(k in hint for k in ("rework", "rwk", "repair")):
        idx = 1
    elif any(k in hint for k in ("review", "fail", "reject", "critical", "human")):
        idx = 2
    else:
        # Deterministic but image-dependent selection.
        seed_source = (filename or "").encode() or image_bytes[:4096] or b"neuron"
        digest = hashlib.sha256(seed_source).digest()
        idx = digest[0] % len(_SCENARIOS)

    name, builder = _SCENARIOS[idx]
    return name, builder()


def _stage_delay(seed: int, stage_index: int) -> float:
    """Deterministic per-stage delay in [_STAGE_DELAY] derived from seed."""
    lo, hi = _STAGE_DELAY
    # Mix seed + stage to vary delays per stage without RNG (RNG is non-deterministic).
    frac = ((seed * 31 + stage_index * 97) % 1000) / 1000.0
    return lo + frac * (hi - lo)


class DemoPipeline:
    """
    Drop-in replacement for :class:`NeuronVisionPipeline` — no Vertex AI required.

    Mirrors the real pipeline's ``run`` / ``run_async`` signatures and emits the
    same ``on_stage`` callbacks ("triage", "solder", "components", "markings",
    "chief") with simulated latency so the live progress UI behaves identically.
    """

    #: Stage keys, in emission order — matches NeuronVisionPipeline.
    STAGES = ("triage", "solder", "components", "markings", "chief")

    def run(
        self,
        image_bytes: bytes,
        on_stage: Callable[[str], None] | None = None,
        filename: str | None = None,
    ) -> PipelineResult:
        """
        Simulate a full QC run, returning a realistic :class:`PipelineResult`.

        Args:
            image_bytes: Raw image bytes (used only to seed scenario selection).
            on_stage:    Optional progress callback, called per stage.
            filename:    Optional source filename — used as a routing hint so
                         operators can force a scenario (e.g. ``board_rework.jpg``).
        """
        t_start = time.perf_counter()
        scenario_name, result = _select_scenario(image_bytes, filename)
        seed = sum(image_bytes[:64]) + len(image_bytes)
        logger.info("DemoPipeline: scenario=%s (simulated, no Vertex AI)", scenario_name)

        for i, stage in enumerate(self.STAGES):
            time.sleep(_stage_delay(seed, i))
            if on_stage:
                on_stage(stage)

        duration = time.perf_counter() - t_start
        result = result.model_copy(update={"duration_seconds": round(duration, 2)})
        logger.info(
            "DemoPipeline: complete in %.2fs — verdict: %s", duration, result.verdict.status
        )
        return result

    async def run_async(
        self,
        image_bytes: bytes,
        on_stage: Callable[[str], None] | None = None,
        filename: str | None = None,
    ) -> PipelineResult:
        """Async variant — same behaviour, awaitable for parity with the real pipeline."""
        t_start = time.perf_counter()
        scenario_name, result = _select_scenario(image_bytes, filename)
        seed = sum(image_bytes[:64]) + len(image_bytes)
        logger.info("DemoPipeline: scenario=%s (simulated async)", scenario_name)

        for i, stage in enumerate(self.STAGES):
            await asyncio.sleep(_stage_delay(seed, i))
            if on_stage:
                on_stage(stage)

        duration = time.perf_counter() - t_start
        result = result.model_copy(update={"duration_seconds": round(duration, 2)})
        return result
