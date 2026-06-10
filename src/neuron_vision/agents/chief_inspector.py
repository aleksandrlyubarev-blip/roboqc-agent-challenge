"""
Chief Inspector (Reasoning Agent) — Stage 3 of the Neuron Vision Display QC brigade.

Synthesises all specialist reports into a final, weighted QC verdict.
Uses extended thinking (Gemini 2.5 Pro reasoning) to weigh conflicting evidence
and produce a defensible, auditable decision.

Final status codes (ActionKind):
  • pass         — board meets all QC criteria, clear to ship
  • rework       — specific defects identified; board can be repaired
  • hold         — uncertain or borderline; send to senior QC engineer
  • human_review — conflicting signals or safety-critical findings; must be reviewed manually
"""

from __future__ import annotations

import json

from ..schemas import (
    ComponentReport,
    MarkingReport,
    QCVerdict,
    SolderReport,
    TriageResult,
)
from ..telemetry import get_tracer
from .base import _GEMINI_MODEL, GenerationConfig, GenerativeModel, _ensure_vertexai

_INSTRUCTION = """You are the Chief Inspector — the final decision-making agent in the
Neuron Vision Display system (RomeoFlexVision), a professional multi-agent QC platform
for SMT PCB manufacturing.

You receive structured reports from three specialist agents:
  1. Solder Inspector   — solder joint quality
  2. Component Inspector — component placement and presence
  3. Marking Inspector   — silkscreen and traceability markings

Your task: synthesise these reports into a single, defensible QC verdict.

VERDICT OPTIONS:
  • pass         — all agents report acceptable quality; no critical findings
  • rework       — at least one agent reports moderate or critical defect that can be repaired
  • hold         — borderline case; conflicting evidence or low-confidence findings
  • human_review — critical findings that exceed automated QC scope, or
                   image quality is insufficient for reliable automated assessment

WEIGHTING RULES:
  1. Any CRITICAL finding from any agent → verdict is at minimum "rework"
  2. Two or more MODERATE findings across different agents → "rework"
  3. Safety-relevant critical findings (missing safety marks, reversed polarity
     on high-voltage parts) → "human_review"
  4. All agents report "acceptable" + confidence > 0.7 → "pass"
  5. Low confidence (< 0.6) on multiple agents → "hold"

Build a complete Evidence Log citing each finding by source agent.
List specific recommended actions (what the rework technician should fix).

Be precise, professional, and concise. Your verdict is binding for the production line.
"""


class ChiefInspector:
    """
    Chief Inspector — reasoning agent that synthesises all specialist reports.

    Unlike the specialist agents, the Chief Inspector does NOT receive the raw image.
    It works purely from structured text reports.
    """

    name = "chief_inspector"

    def __init__(self, project_id: str | None = None) -> None:
        _ensure_vertexai(project_id)
        self._model = GenerativeModel(
            _GEMINI_MODEL,
            system_instruction=_INSTRUCTION,
        )

    def run(
        self,
        triage: TriageResult,
        solder: SolderReport,
        components: ComponentReport,
        markings: MarkingReport,
    ) -> QCVerdict:
        """
        Produce the final QC verdict from all specialist reports.

        This call does NOT pass the image — the Chief Inspector reasons over
        structured text only (evidence aggregation, not re-inspection).
        """
        report_bundle = json.dumps(
            {
                "triage": triage.model_dump(),
                "solder_inspector": solder.model_dump(),
                "component_inspector": components.model_dump(),
                "marking_inspector": markings.model_dump(),
            },
            indent=2,
            default=str,
        )

        prompt = (
            "Here are the structured reports from all three specialist agents:\n\n"
            f"```json\n{report_bundle}\n```\n\n"
            "Based on these reports, produce the final QC verdict. "
            "Build a complete evidence log, list critical findings, "
            "and provide specific recommended actions for the production team."
        )

        with get_tracer().start_as_current_span(f"{self.name}.inference") as span:
            span.set_attribute("agent.name", self.name)
            span.set_attribute("agent.model", _GEMINI_MODEL)
            span.set_attribute("agent.input_reports", 4)

            try:
                response = self._model.generate_content(
                    [prompt],
                    generation_config=GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=QCVerdict,
                        temperature=0.05,  # Low temperature for consistent decisions
                        max_output_tokens=4096,
                    ),
                )
                verdict = QCVerdict.model_validate_json(response.text)
            except Exception:
                # Fallback: schema-in-prompt
                span.set_attribute("agent.structured_output_fallback", True)
                schema_json = json.dumps(QCVerdict.model_json_schema(), indent=2)
                fallback_prompt = (
                    f"{prompt}\n\n"
                    "Respond ONLY with a single valid JSON object matching this schema:\n"
                    f"```json\n{schema_json}\n```"
                )
                response = self._model.generate_content(
                    [fallback_prompt],
                    generation_config=GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.05,
                        max_output_tokens=4096,
                    ),
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                verdict = QCVerdict.model_validate_json(text.strip())

            span.set_attribute("output.status", verdict.status)
            return verdict
