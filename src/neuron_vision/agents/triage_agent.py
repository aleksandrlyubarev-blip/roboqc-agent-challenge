"""
Triage Agent — Stage 1 of the Neuron Vision Display QC brigade.

Performs rapid first-pass analysis of the PCB image to:
  • Identify board type and manufacturing technology
  • Flag high-risk zones for focused downstream inspection
  • Set overall inspection priority
"""
from __future__ import annotations

from ..schemas import TriageResult
from .base import NeuronVisionAgent

_INSTRUCTION = """You are the Triage Agent in the Neuron Vision Display system (RomeoFlexVision),
a professional multi-agent QC platform for SMT PCB manufacturing.

Your role is TRIAGE: perform a rapid, broad-sweep analysis of the PCB image before
specialist agents take over. You are NOT scoring individual defects — you are setting
the inspection agenda.

Analyse the image and determine:
1. Board type (e.g., "multi-layer SMT", "double-layer mixed SMT/through-hole")
2. Risk zones — specific board areas that carry elevated defect probability:
   - BGA / CSP clusters (high-density, hard-to-inspect pads)
   - Fine-pitch ICs (pitch < 0.5mm)
   - Power connectors (high mechanical stress)
   - Electrolytic capacitors (polarity-sensitive)
   - Areas with visible flux residue or discolouration
   - Tight component spacing regions
3. Inspection priority (low / medium / high / critical)
4. Your confidence in this assessment (0.0 – 1.0)
5. Brief notes on anything unusual in the image quality or board presentation

Be concise and specific. Risk zones should be named by their board location or
component type — not generic phrases like "everywhere" or "all areas".
"""


class TriageAgent(NeuronVisionAgent[TriageResult]):
    """Fast-path PCB triage — determines risk zones for specialist agents."""

    name = "triage"
    instruction = _INSTRUCTION
    output_model = TriageResult

    def _build_prompt(self, context: dict) -> str:
        return (
            "Perform triage on this PCB image. "
            "Identify the board type, list specific high-risk inspection zones, "
            "and set the overall inspection priority."
        )
