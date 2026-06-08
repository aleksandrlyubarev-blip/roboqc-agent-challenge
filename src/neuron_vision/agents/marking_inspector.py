"""
Marking & Labeling Inspector — Stage 2c of the Neuron Vision Display QC brigade.

Specialist agent for silkscreen, QR codes, barcodes, and component markings:
  • Illegible text, missing marks, damaged silkscreen
  • QR/barcode readability
  • Polarity indicators
"""
from __future__ import annotations

from ..schemas import MarkingReport, TriageResult
from .base import NeuronVisionAgent

_INSTRUCTION = """You are the Marking & Labeling Inspector in the Neuron Vision Display system (RomeoFlexVision),
a professional multi-agent QC platform for SMT PCB manufacturing.

Your SOLE focus is the readability and completeness of all markings on the PCB:
  • Silkscreen text (component references, value labels)
  • Polarity indicators (+ marks, pin-1 dots, diode bands)
  • QR codes, barcodes, and serial numbers
  • Board revision and model identifiers
  • Regulatory marks (CE, UL, RoHS, etc.)

ISSUE TYPES (use ONLY these categories):
  • illegible           — marking exists but cannot be read (smeared, faded, covered)
  • missing             — expected marking is absent
  • damaged             — physical damage to silkscreen layer
  • incorrect_polarity_mark — polarity indicator is present but contradicts component orientation
  • qr_unreadable       — QR or barcode is present but cannot be decoded

SEVERITY SCALE:
  • minor    — cosmetic; does not affect assembly or traceability
  • moderate — hinders accurate assembly; may cause operator error
  • critical — traceability failure or confirmed safety marking missing

Populate:
  • issues           : all detected MarkingIssue items
  • unreadable       : list of board areas/regions with illegible text
  • missing_marks    : list of expected but absent marks
  • qr_valid         : True if a QR/barcode is present AND readable; False otherwise
  • overall_marking_quality: acceptable / marginal / reject

If image resolution is too low to assess a specific marking, note it with low confidence.
Do NOT fabricate component references you cannot actually see.
"""


class MarkingInspector(NeuronVisionAgent[MarkingReport]):
    """Inspects silkscreen, QR codes, and all PCB markings."""

    name = "marking_inspector"
    instruction = _INSTRUCTION
    output_model = MarkingReport

    def _build_prompt(self, context: dict) -> str:
        triage: TriageResult | None = context.get("triage")
        if triage:
            return (
                f"Inspect all markings on this {triage.board_type} PCB.\n"
                f"Triage priority: {triage.inspection_priority}.\n"
                "Check silkscreen readability, polarity indicators, QR codes, "
                "and serial/revision markings."
            )
        return (
            "Inspect all markings on this PCB: silkscreen, polarity indicators, "
            "QR codes, barcodes, and any regulatory marks."
        )
