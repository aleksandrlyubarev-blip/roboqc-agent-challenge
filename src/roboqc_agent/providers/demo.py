"""Offline demo provider — deterministic, no Vertex AI credentials required.

The demo provider implements the same ``generate_multimodal`` / ``generate_text``
surface as ``VertexGeminiProvider`` but returns deterministic, taxonomy-consistent
results so the Streamlit demo and the test suite run with no GCP access. It is a
demonstration aid, never the submission's inference path.

Detections are seeded from the image path, so a given image always yields the
same defects (it looks live) while different images differ. FMEA mappings are
read straight from the frozen taxonomy.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from roboqc_agent.agents.fmea_risk import FMEAObservation
from roboqc_agent.agents.vision_inspector import DefectObservation
from roboqc_agent.providers.vertex_gemini import GenerationResult
from roboqc_agent.schemas import BBox, DefectClass
from roboqc_agent.taxonomy import TAXONOMY

_MAX_DEMO_DEFECTS = 3
_TILE_PX = 480


class DemoProvider:
    """Deterministic offline stand-in for ``VertexGeminiProvider``."""

    def generate_multimodal(
        self,
        images: Sequence[str | Path],
        prompt: str,
        *,
        response_schema: Any | None = None,
    ) -> GenerationResult:
        seed = self._seed(str(images[0]) if images else prompt)
        count = seed % (_MAX_DEMO_DEFECTS + 1)
        classes = list(DefectClass)
        observations: list[DefectObservation] = []
        for i in range(count):
            cls = classes[(seed >> (i * 5)) % len(classes)]
            entry = TAXONOMY[cls]
            confidence = round(0.55 + ((seed >> (i * 3)) % 45) / 100, 2)
            observations.append(
                DefectObservation(
                    defect_class=cls,
                    bbox=BBox(
                        x=(seed >> (i * 7)) % _TILE_PX,
                        y=(seed >> (i * 11)) % _TILE_PX,
                        w=24,
                        h=24,
                    ),
                    confidence=confidence,
                    source=entry.source,
                )
            )
        return GenerationResult(text=None, parsed=observations, raw={"demo": True})

    def generate_text(
        self,
        prompt: str,
        *,
        response_schema: Any | None = None,
    ) -> GenerationResult:
        observations: list[FMEAObservation] = []
        for name in re.findall(r"defect_class=(\w+)", prompt):
            try:
                cls = DefectClass(name)
            except ValueError:
                continue
            entry = TAXONOMY[cls]
            observations.append(
                FMEAObservation(
                    severity=entry.severity,
                    default_action=entry.default_action,
                    justification=(
                        f"{cls.value.replace('_', ' ').capitalize()} maps to "
                        f"{entry.severity.value} severity per the frozen taxonomy."
                    ),
                    escalate_to_senior=entry.always_escalate,
                )
            )
        return GenerationResult(text=None, parsed=observations, raw={"demo": True})

    @staticmethod
    def _seed(value: str) -> int:
        return int(hashlib.sha256(value.encode()).hexdigest(), 16)


__all__ = ["DemoProvider"]
