"""
Demo Mode — Neuron Vision Display (RomeoFlexVision)

Drop-in replacement for NeuronVisionPipeline that runs without Vertex AI.
Provides three realistic QC scenarios for live hackathon demonstrations.

Activate via:
  - Environment variable: DEMO_MODE=true
  - Or pass demo_mode=True to DemoPipeline.__init__()
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable

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

# ---------------------------------------------------------------------------
# Scenario 1: PASS — clean board, one minor solder concern
# ---------------------------------------------------------------------------


def _scenario_pass() -> PipelineResult:
    triage = TriageResult(
        board_type="Double-layer SMT (mixed SMD + through-hole)",
        risk_zones=["Fine-pitch IC U3 (0.5mm pitch)", "Electrolytic caps C12–C15"],
        inspection_priority="medium",
        confidence=0.94,
        notes="Good image quality. Board appears clean with no visible contamination.",
    )
    solder = SolderReport(
        defects=[
            SolderDefect(
                defect_type="insufficient_solder",
                location="R12 pin 2",
                severity="minor",
                confidence=0.71,
            )
        ],
        overall_solder_quality="acceptable",
        inspected_joints_estimate=284,
        confidence=0.91,
        summary=(
            "284 joints inspected. One minor under-fill on R12 pin 2 — within acceptable "
            "tolerance. All other joints show good wetting and fillet formation."
        ),
    )
    components = ComponentReport(
        issues=[],
        missing=[],
        misoriented=[],
        shifted=[],
        overall_placement_quality="acceptable",
        confidence=0.96,
        summary=(
            "All components present and correctly placed. No orientation or shift issues detected."
        ),
    )
    markings = MarkingReport(
        issues=[],
        unreadable=[],
        missing_marks=[],
        qr_valid=True,
        overall_marking_quality="acceptable",
        confidence=0.93,
        summary=(
            "All silkscreen markings legible. QR code scanned successfully. Polarity indicators "
            "present on all polarised components."
        ),
    )
    verdict = QCVerdict(
        status="pass",
        evidence_log=[
            EvidenceEntry(
                source_agent="triage",
                finding="Board type confirmed: double-layer SMT. Medium priority inspection.",
                severity="info",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Minor under-fill on R12 pin 2 — within tolerance, no functional risk.",
                severity="minor",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="All 47 components present and correctly placed.",
                severity="info",
            ),
            EvidenceEntry(
                source_agent="marking_inspector",
                finding="QR code valid. All silkscreen markings legible.",
                severity="info",
            ),
        ],
        critical_findings=[],
        confidence=0.93,
        summary=(
            "Board meets QC criteria. One minor solder concern on R12 is within tolerance. Clear "
            "to proceed to final test."
        ),
        recommended_actions=[
            "Optional: reflow R12 pin 2 solder joint at next opportunity (non-blocking)"
        ],
    )
    return PipelineResult(
        triage=triage,
        solder=solder,
        components=components,
        markings=markings,
        verdict=verdict,
        duration_seconds=8.4,
    )


# ---------------------------------------------------------------------------
# Scenario 2: REWORK — solder bridges + shifted component
# ---------------------------------------------------------------------------


def _scenario_rework() -> PipelineResult:
    triage = TriageResult(
        board_type="Multi-layer SMT (4-layer, BGA + fine-pitch ICs)",
        risk_zones=[
            "BGA cluster U1 (0.8mm pitch, 256-ball)",
            "Fine-pitch IC U5 (0.4mm pitch)",
            "Power connector J3",
        ],
        inspection_priority="high",
        confidence=0.89,
        notes="Visible flux residue near J3. BGA region requires close attention.",
    )
    solder = SolderReport(
        defects=[
            SolderDefect(
                defect_type="solder_bridge",
                location="U5 pins 14–15",
                severity="critical",
                confidence=0.93,
            ),
            SolderDefect(
                defect_type="cold_joint", location="J3 pin 4", severity="moderate", confidence=0.82
            ),
            SolderDefect(
                defect_type="excess_solder",
                location="C4 positive pad",
                severity="minor",
                confidence=0.76,
            ),
        ],
        overall_solder_quality="reject",
        inspected_joints_estimate=412,
        confidence=0.88,
        summary=(
            "Critical solder bridge detected between U5 pins 14–15 — short circuit risk. Cold "
            "joint at J3 pin 4. Minor excess solder at C4."
        ),
    )
    components = ComponentReport(
        issues=[
            ComponentIssue(
                component_ref="R7",
                issue_type="shifted",
                severity="moderate",
                confidence=0.85,
                details="Shifted ~0.3mm south, one pad edge exposed. Risk of intermittent contact.",
            )
        ],
        missing=[],
        misoriented=[],
        shifted=["R7"],
        overall_placement_quality="marginal",
        confidence=0.87,
        summary=(
            "R7 is shifted 0.3mm — may cause intermittent contact. All other components placed "
            "correctly."
        ),
    )
    markings = MarkingReport(
        issues=[
            MarkingIssue(area="J3 area", issue_type="illegible", severity="minor", confidence=0.78)
        ],
        unreadable=["J3 connector label"],
        missing_marks=[],
        qr_valid=True,
        overall_marking_quality="acceptable",
        confidence=0.88,
        summary=(
            "Silkscreen near J3 partially obscured by flux residue. QR code valid. All polarity "
            "marks visible."
        ),
    )
    verdict = QCVerdict(
        status="rework",
        evidence_log=[
            EvidenceEntry(
                source_agent="triage",
                finding="High-risk zones: BGA U1, fine-pitch U5, power connector J3.",
                severity="info",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="CRITICAL: Solder bridge between U5 pins 14–15 — guaranteed short circuit.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Cold joint at J3 pin 4 — intermittent connection risk.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Excess solder at C4 positive pad — cosmetic, no functional impact.",
                severity="minor",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="R7 shifted 0.3mm south — edge pad exposure, moderate risk.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="marking_inspector",
                finding="J3 label partially obscured by flux residue.",
                severity="minor",
            ),
        ],
        critical_findings=["Solder bridge U5 pins 14–15 (short circuit risk)"],
        confidence=0.91,
        summary=(
            "Board requires rework. Critical solder bridge on U5 must be resolved before testing. "
            "R7 placement and J3 cold joint also need attention."
        ),
        recommended_actions=[
            "Remove solder bridge between U5 pins 14–15 using solder wick",
            "Reflow cold joint at J3 pin 4 with flux",
            "Realign and reflow R7 (0.3mm south shift)",
            "Clean flux residue near J3 and verify label readability",
        ],
    )
    return PipelineResult(
        triage=triage,
        solder=solder,
        components=components,
        markings=markings,
        verdict=verdict,
        duration_seconds=11.2,
    )


# ---------------------------------------------------------------------------
# Scenario 3: HUMAN REVIEW — missing component + critical issues
# ---------------------------------------------------------------------------


def _scenario_human_review() -> PipelineResult:
    triage = TriageResult(
        board_type="Single-layer SMT (consumer electronics)",
        risk_zones=[
            "Power management IC U2",
            "Bulk capacitors C1–C3 (polarised)",
            "Test points TP1–TP8",
        ],
        inspection_priority="critical",
        confidence=0.87,
        notes=(
            "Image quality adequate but oblique angle reduces confidence on fine-pitch areas. "
            "Possible burn mark visible near U2."
        ),
    )
    solder = SolderReport(
        defects=[
            SolderDefect(
                defect_type="cold_joint", location="U2 pin 1", severity="critical", confidence=0.88
            ),
            SolderDefect(
                defect_type="void", location="U2 pin 3", severity="critical", confidence=0.79
            ),
            SolderDefect(
                defect_type="insufficient_solder",
                location="L1 output pad",
                severity="moderate",
                confidence=0.83,
            ),
        ],
        overall_solder_quality="reject",
        inspected_joints_estimate=178,
        confidence=0.84,
        summary=(
            "Multiple critical defects around power IC U2. Cold joint and suspected void are "
            "safety-relevant in a power path."
        ),
    )
    components = ComponentReport(
        issues=[
            ComponentIssue(
                component_ref="C2",
                issue_type="missing",
                severity="critical",
                confidence=0.96,
                details=(
                    "Bulk decoupling cap C2 (100µF) not populated — power rail instability risk."
                ),
            ),
            ComponentIssue(
                component_ref="C1",
                issue_type="misoriented",
                severity="critical",
                confidence=0.91,
                details=(
                    "Electrolytic capacitor C1 reversed — anode/cathode swapped, will fail under "
                    "power."
                ),
            ),
        ],
        missing=["C2"],
        misoriented=["C1"],
        shifted=[],
        overall_placement_quality="reject",
        confidence=0.90,
        summary=(
            "C2 missing (power decoupling). C1 installed with reversed polarity — critical safety "
            "risk if powered."
        ),
    )
    markings = MarkingReport(
        issues=[
            MarkingIssue(
                area="U2 region", issue_type="damaged", severity="moderate", confidence=0.82
            ),
            MarkingIssue(
                area="QR code", issue_type="qr_unreadable", severity="moderate", confidence=0.95
            ),
            MarkingIssue(
                area="C1 polarity mark",
                issue_type="incorrect_polarity_mark",
                severity="critical",
                confidence=0.88,
            ),
        ],
        unreadable=["U2 area silkscreen"],
        missing_marks=[],
        qr_valid=False,
        overall_marking_quality="reject",
        confidence=0.86,
        summary=(
            "Silkscreen near U2 appears heat-damaged. QR code unreadable — traceability "
            "compromised. Polarity mark on C1 may be incorrect."
        ),
    )
    verdict = QCVerdict(
        status="human_review",
        evidence_log=[
            EvidenceEntry(
                source_agent="triage",
                finding="Possible burn mark near U2 — critical visual indicator.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Cold joint + void at U2 (power IC) — safety-critical path.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="solder_inspector",
                finding="Insufficient solder on L1 output pad.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="C2 (100µF bulk cap) missing — power rail will be unstable.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="component_inspector",
                finding="C1 reversed polarity — SAFETY HAZARD, do not power.",
                severity="critical",
            ),
            EvidenceEntry(
                source_agent="marking_inspector",
                finding="QR code unreadable — traceability chain broken.",
                severity="moderate",
            ),
            EvidenceEntry(
                source_agent="marking_inspector",
                finding="Silkscreen near U2 heat-damaged — possible prior thermal event.",
                severity="moderate",
            ),
        ],
        critical_findings=[
            "C1 reversed polarity — DO NOT POWER (electrolytic cap will vent/explode)",
            "C2 missing — power rail instability",
            "U2 solder joints critical — cold joint + void in power path",
            "QR traceability broken",
        ],
        confidence=0.88,
        summary=(
            "DO NOT POWER. Multiple safety-critical findings: reversed polarised cap (C1), missing "
            "decoupling cap (C2), compromised power IC solder joints. Escalate to senior QC "
            "engineer immediately."
        ),
        recommended_actions=[
            "DO NOT POWER THIS BOARD under any circumstances",
            "Remove and correctly reinstall C1 (check polarity mark orientation)",
            "Populate missing C2 (100µF bulk decoupling capacitor)",
            "Rework U2 solder joints — reflow pin 1 (cold joint) and pin 3 (void)",
            "Inspect U2 for thermal damage — replace if burn mark confirmed",
            "Re-print QR code label for traceability",
        ],
    )
    return PipelineResult(
        triage=triage,
        solder=solder,
        components=components,
        markings=markings,
        verdict=verdict,
        duration_seconds=13.7,
    )


# ---------------------------------------------------------------------------
# Scenario selector
# ---------------------------------------------------------------------------

_SCENARIOS = {
    "pass": _scenario_pass,
    "rework": _scenario_rework,
    "human_review": _scenario_human_review,
}

_SCENARIO_KEYS = list(_SCENARIOS.keys())

_STAGE_DELAYS = {
    "triage": 1.2,
    "solder": 2.1,
    "components": 1.8,
    "markings": 1.5,
    "chief": 2.4,
}


def _pick_scenario(image_bytes: bytes) -> str:
    """Deterministic scenario selection based on image content hash."""
    digest = hashlib.md5(image_bytes[:4096]).hexdigest()
    index = int(digest[:2], 16) % len(_SCENARIO_KEYS)
    return _SCENARIO_KEYS[index]


# ---------------------------------------------------------------------------
# DemoPipeline — drop-in replacement for NeuronVisionPipeline
# ---------------------------------------------------------------------------


class DemoPipeline:
    """
    Demo-mode pipeline for Neuron Vision Display.

    Runs without Vertex AI credentials — returns pre-built realistic
    QC scenarios with simulated per-agent processing delays.

    Interface is identical to NeuronVisionPipeline.run().
    """

    STAGE_ORDER = ["triage", "solder", "components", "markings", "chief"]

    def __init__(self, scenario: str | None = None, speed: float = 1.0) -> None:
        """
        Args:
            scenario: Force a specific scenario ('pass', 'rework', 'human_review').
                      If None, scenario is chosen deterministically from image hash.
            speed:    Delay multiplier. 0.0 = instant, 1.0 = normal, 2.0 = slow.
        """
        self._scenario = scenario
        self._speed = speed

    def run(
        self,
        image_bytes: bytes,
        on_stage: Callable[[str], None] | None = None,
    ) -> PipelineResult:
        """
        Simulate the 5-agent pipeline with realistic delays.

        Args:
            image_bytes: Raw image bytes (used for scenario selection if not forced).
            on_stage:    Progress callback — same interface as NeuronVisionPipeline.
        """
        scenario_key = self._scenario or _pick_scenario(image_bytes)
        builder = _SCENARIOS.get(scenario_key, _scenario_rework)

        # Simulate per-stage processing
        for stage in self.STAGE_ORDER:
            delay = _STAGE_DELAYS.get(stage, 1.5) * self._speed
            if delay > 0:
                time.sleep(delay)
            if on_stage:
                on_stage(stage)

        result = builder()
        return result

    @classmethod
    def available_scenarios(cls) -> list[str]:
        return _SCENARIO_KEYS
