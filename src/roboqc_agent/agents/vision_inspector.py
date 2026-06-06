"""ADK factory for the Vision Inspector agent.

The model observes defect *candidates* on one tile; it does not know the tile or
defect identities. The factory therefore declares ``DefectObservation`` as the
structured output (class, bbox, confidence, source) and ``to_defects`` links
each observation to its ``Tile`` — assigning ``tile_id``/``defect_id``, applying
the confidence floor, and deduplicating overlapping detections (architecture
§2.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from google.adk.agents.llm_agent import Agent
from pydantic import BaseModel, Field

from roboqc_agent.schemas import BBox, Defect, DefectClass
from roboqc_agent.taxonomy import DefectSource

VISION_INSPECTOR_NAME = "vision_inspector"

# Detections below this normalized confidence are dropped at the Vision Inspector
# boundary — they create downstream noise and false-positive overload (§2.1).
CONFIDENCE_FLOOR = 0.50

# Coarse spatial bucket (pixels) used to deduplicate overlapping detections of
# the same class within one tile.
_DEDUP_BUCKET_PX = 16


class DefectObservation(BaseModel):
    """One defect candidate as observed by the model, before tile linkage."""

    defect_class: DefectClass
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)
    source: DefectSource = Field(
        description=(
            "labeled_detector for the 6 DeepPCB classes, anomaly_arm for the "
            "4 anomaly-detected classes"
        )
    )


def build_vision_inspector_agent(
    *,
    instruction: str,
    model: str = "gemini-2.5-pro",
) -> Agent:
    """Build the multimodal Vision Inspector without owning prompt text."""

    return Agent(
        name=VISION_INSPECTOR_NAME,
        description="Inspects one SMT microscope tile and emits defect candidates.",
        model=model,
        instruction=instruction,
        output_schema=list[DefectObservation],
        include_contents="none",
    )


def to_defects(
    observations: Sequence[DefectObservation],
    tile_id: UUID,
    *,
    confidence_floor: float = CONFIDENCE_FLOOR,
) -> list[Defect]:
    """Link observations to a tile, applying the confidence floor and dedup.

    Highest-confidence detection wins when two observations of the same class
    fall in the same coarse spatial bucket.
    """

    ordered = sorted(observations, key=lambda obs: obs.confidence, reverse=True)
    seen: set[tuple[DefectClass, int, int]] = set()
    defects: list[Defect] = []
    for obs in ordered:
        if obs.confidence < confidence_floor:
            continue
        key = (
            obs.defect_class,
            obs.bbox.x // _DEDUP_BUCKET_PX,
            obs.bbox.y // _DEDUP_BUCKET_PX,
        )
        if key in seen:
            continue
        seen.add(key)
        defects.append(
            Defect(
                tile_id=tile_id,
                defect_class=obs.defect_class,
                bbox=obs.bbox,
                confidence=obs.confidence,
                source=obs.source,
            )
        )
    return defects


__all__ = [
    "VISION_INSPECTOR_NAME",
    "CONFIDENCE_FLOOR",
    "DefectObservation",
    "build_vision_inspector_agent",
    "to_defects",
]
