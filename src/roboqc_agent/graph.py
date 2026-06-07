"""Per-tile inspection pipeline wiring the four RoboQC agents.

``RoboQCPipeline`` executes the sequential composition from architecture §5.1:

    Vision Inspector → FMEA Risk → Supervisor → Evidence Report

Vision Inspector and FMEA Risk are the two ADK ``LlmAgent`` definitions; the
pipeline drives them through the injected Vertex provider using each agent's
structured-output contract. Supervisor and Evidence Report are deterministic
stages (architecture §2.4, §2.3). The provider is injected, so the whole
pipeline runs offline in tests and demos with a fake/demo provider.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from roboqc_agent.agents.evidence_report import assemble_tile_report
from roboqc_agent.agents.fmea_risk import FMEAObservation, to_fmea_entries
from roboqc_agent.agents.supervisor import decide_action
from roboqc_agent.agents.vision_inspector import DefectObservation, to_defects
from roboqc_agent.policy import FrictionPolicyEngine
from roboqc_agent.prompts import FMEA_RISK_INSTRUCTION, VISION_INSPECTOR_INSTRUCTION
from roboqc_agent.schemas import Defect, FMEAEntry, Tile, TileReport

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class GenerationLike(Protocol):
    """The subset of the provider's result that the pipeline consumes."""

    text: str | None
    parsed: Any


class InspectionProvider(Protocol):
    """Multimodal + text generation surface (see ``VertexGeminiProvider``)."""

    def generate_multimodal(
        self,
        images: Sequence[str | Path],
        prompt: str,
        *,
        response_schema: Any | None = None,
    ) -> GenerationLike: ...

    def generate_text(
        self,
        prompt: str,
        *,
        response_schema: Any | None = None,
    ) -> GenerationLike: ...


def _coerce_list(payload: Any, model: type[_ModelT]) -> list[_ModelT]:
    if payload is None:
        return []
    items = payload if isinstance(payload, list) else [payload]
    coerced: list[_ModelT] = []
    for item in items:
        if isinstance(item, model):
            coerced.append(item)
        elif isinstance(item, BaseModel):
            coerced.append(model.model_validate(item.model_dump()))
        else:
            coerced.append(model.model_validate(item))
    return coerced


def _parse_models(result: GenerationLike, model: type[_ModelT]) -> list[_ModelT]:
    """Read structured output from the provider, falling back to raw JSON text."""

    if result.parsed is not None:
        return _coerce_list(result.parsed, model)
    if result.text:
        return _coerce_list(json.loads(result.text), model)
    return []


class RoboQCPipeline:
    """Runs the four-agent per-tile inspection flow end to end."""

    def __init__(
        self,
        provider: InspectionProvider,
        *,
        vision_instruction: str = VISION_INSPECTOR_INSTRUCTION,
        fmea_instruction: str = FMEA_RISK_INSTRUCTION,
        policy: FrictionPolicyEngine | None = None,
    ) -> None:
        self.provider = provider
        self.vision_instruction = vision_instruction
        self.fmea_instruction = fmea_instruction
        self.policy = policy or FrictionPolicyEngine()

    def inspect_tile(self, tile: Tile, image_path: str | Path) -> TileReport:
        """Inspect one tile and return its assembled evidence record."""

        defects = self._detect_defects(tile, image_path)
        fmea_entries = self._assess_risk(defects) if defects else []
        action = decide_action(tile.tile_id, defects, fmea_entries, policy=self.policy)
        return assemble_tile_report(tile, defects, fmea_entries, action)

    def _detect_defects(self, tile: Tile, image_path: str | Path) -> list[Defect]:
        result = self.provider.generate_multimodal(
            [str(image_path)],
            self.vision_instruction,
            response_schema=list[DefectObservation],
        )
        observations = _parse_models(result, DefectObservation)
        return to_defects(observations, tile.tile_id)

    def _assess_risk(self, defects: Sequence[Defect]) -> list[FMEAEntry]:
        result = self.provider.generate_text(
            self._fmea_prompt(defects),
            response_schema=list[FMEAObservation],
        )
        observations = _parse_models(result, FMEAObservation)
        return to_fmea_entries(observations, defects)

    def _fmea_prompt(self, defects: Sequence[Defect]) -> str:
        lines = [
            f"{index}. defect_class={defect.defect_class.value}, "
            f"confidence={defect.confidence:.2f}, source={defect.source}"
            for index, defect in enumerate(defects)
        ]
        return (
            f"{self.fmea_instruction}\n\n"
            "Defects on this tile (return one FMEA entry per line, same order):\n"
            + "\n".join(lines)
        )


__all__ = [
    "GenerationLike",
    "InspectionProvider",
    "RoboQCPipeline",
]
