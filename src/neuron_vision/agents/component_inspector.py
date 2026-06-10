"""
Component Inspector — Stage 2b of the Neuron Vision Display QC brigade.

Specialist agent for component placement quality:
  • Missing, wrong-value, misoriented, shifted, tombstoned, or damaged components
"""

from __future__ import annotations

from typing import Any

from ..schemas import ComponentReport, TriageResult
from .base import NeuronVisionAgent

_INSTRUCTION = """You are the Component Inspector in the Neuron Vision Display system
(RomeoFlexVision),
a professional multi-agent QC platform for SMT PCB manufacturing.

Your SOLE focus is component placement and presence. Do not comment on solder quality
or silkscreen markings unless they directly reveal a placement issue.

For every component visible on the board, evaluate:

ISSUE TYPES (use ONLY these categories):
  • missing       — pad/footprint is present but no component is placed
  • wrong_value   — component is present but appears to be wrong type (e.g., wrong package size)
  • misoriented   — component is rotated incorrectly (e.g., polarised cap reversed)
  • shifted       — component is placed off-center but still making contact
  • tombstoned    — component is standing vertically on one pad
  • damaged       — component body is visibly cracked, burnt, or delaminated

SEVERITY SCALE:
  • minor    — barely misaligned, does not affect function
  • moderate — significant shift/rotation, may cause intermittent contact issues
  • critical — missing component, reversed polarity part, or severe damage

Populate the following fields:
  • issues        : list of all detected ComponentIssue items
  • missing       : list of component refs confirmed missing (subset of issues)
  • misoriented   : list of refs with wrong orientation
  • shifted       : list of refs with placement shift
  • overall_placement_quality: acceptable / marginal / reject

If a component reference is not visible in the image or is blocked by another component,
do not guess — skip it or note with low confidence.
"""


class ComponentInspector(NeuronVisionAgent[ComponentReport]):
    """Inspects component placement, presence, and orientation."""

    name = "component_inspector"
    instruction = _INSTRUCTION
    output_model = ComponentReport

    def _build_prompt(self, context: dict[str, Any]) -> str:
        triage: TriageResult | None = context.get("triage")
        if triage:
            zones = ", ".join(triage.risk_zones) if triage.risk_zones else "none flagged"
            return (
                f"Inspect component placement on this {triage.board_type} PCB.\n"
                f"Triage priority: {triage.inspection_priority}.\n"
                f"High-risk zones: {zones}.\n"
                "Check for missing, misoriented, shifted, or damaged components."
            )
        return (
            "Inspect component placement on this PCB. "
            "Identify all missing, misoriented, shifted, tombstoned, or damaged components."
        )
