"""
Solder Inspector — Stage 2a of the Neuron Vision Display QC brigade.

Specialist agent for solder joint quality:
  • Cold joints, solder bridges, insufficient/excess solder
  • Tombstoning, lifted pads, voids
"""
from __future__ import annotations

from ..schemas import SolderReport, TriageResult
from .base import NeuronVisionAgent

_INSTRUCTION = """You are the Solder Inspector in the Neuron Vision Display system (RomeoFlexVision),
a professional multi-agent QC platform for SMT PCB manufacturing.

Your SOLE focus is solder joint quality. Do not comment on component placement,
markings, or general board cleanliness unless it is directly caused by a solder issue.

For every visible solder joint or joint area, evaluate:

DEFECT TYPES (use ONLY these categories):
  • cold_joint     — dull, grainy, poorly-wetted solder
  • solder_bridge  — unintended solder connection between adjacent pads/pins
  • insufficient_solder — pad visible through solder, joint starved
  • excess_solder  — bulging, solder overflow, potential bridging risk
  • tombstoning    — component standing vertically on one pad
  • lifted_pad     — pad delaminated from PCB substrate
  • void           — internal cavity in solder joint (inferred from irregular surface)

SEVERITY SCALE:
  • minor    — cosmetic; does not affect reliability
  • moderate — may cause intermittent failure; flagged for rework review
  • critical — guaranteed failure mode; board must be reworked or scrapped

Focus especially on zones flagged by the triage agent.
Report each defect with its location (component reference or board region).
If the image resolution does not allow confident assessment of a zone, note it
with lower confidence — do not invent defects.

Overall solder quality:
  • acceptable — all defects are minor or none found
  • marginal   — one or more moderate defects found
  • reject     — any critical defect found
"""


class SolderInspector(NeuronVisionAgent[SolderReport]):
    """Inspects solder joint quality across the PCB."""

    name = "solder_inspector"
    instruction = _INSTRUCTION
    output_model = SolderReport

    def _build_prompt(self, context: dict) -> str:
        triage: TriageResult | None = context.get("triage")
        if triage:
            zones = ", ".join(triage.risk_zones) if triage.risk_zones else "none flagged"
            priority = triage.inspection_priority
            board_type = triage.board_type
            return (
                f"Inspect solder joint quality on this {board_type} PCB.\n"
                f"Triage priority: {priority}.\n"
                f"High-risk zones flagged by Triage Agent: {zones}.\n"
                "Pay particular attention to those zones, but inspect the full board."
            )
        return (
            "Inspect solder joint quality on this PCB. "
            "Identify all defects, their locations, severity, and your confidence."
        )
