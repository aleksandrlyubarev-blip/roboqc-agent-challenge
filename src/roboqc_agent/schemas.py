"""
RoboQC Agent — Pydantic schemas.

Single source of truth for inter-agent contracts. Vision Inspector emits Defect,
FMEA Risk emits FMEAEntry, Evidence Report emits TileReport / QCReport,
Supervisor emits Action.

Frozen 2026-05-16 for Google submission.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DefectClass(StrEnum):
    OPEN_TRACE = "open_trace"
    SHORT_CIRCUIT = "short_circuit"
    MOUSEBITE = "mousebite"
    SPUR = "spur"
    EXCESS_COPPER = "excess_copper"
    PINHOLE = "pinhole"
    TOMBSTONING = "tombstoning"
    SOLDER_BRIDGE = "solder_bridge"
    INSUFFICIENT_SOLDER = "insufficient_solder"
    MISSING_COMPONENT = "missing_component"


class Severity(StrEnum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class ActionKind(StrEnum):
    PASS = "pass"
    REWORK = "rework"
    HOLD = "hold"
    HUMAN_REVIEW = "human_review"


class OperatorAction(StrEnum):
    ACCEPT = "accept"
    OVERRIDE = "override"


class BoardStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETE_PASS = "pass"
    COMPLETE_REWORK = "rework"
    COMPLETE_HOLD = "hold"


class LotStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    HOLD_FOR_ENGINEERING = "hold_for_engineering_review"


# ---------------------------------------------------------------------------
# Geometric primitives
# ---------------------------------------------------------------------------


class BBox(BaseModel):
    """Bounding box in tile-pixel coordinates."""

    model_config = ConfigDict(frozen=True)

    x: int = Field(ge=0, description="left edge, pixels")
    y: int = Field(ge=0, description="top edge, pixels")
    w: int = Field(gt=0, description="width, pixels")
    h: int = Field(gt=0, description="height, pixels")


class TilePosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: int = Field(ge=0)
    col: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Tile (input)
# ---------------------------------------------------------------------------


class Tile(BaseModel):
    """A single microscope-tile capture submitted for inspection."""

    tile_id: UUID = Field(default_factory=uuid4)
    board_id: str
    lot_id: str
    position: TilePosition
    magnification: Literal[5, 10, 20, 40]
    image_uri: str = Field(description="GCS URI of stored capture")
    captured_at: datetime
    operator_id: str


# ---------------------------------------------------------------------------
# Vision Inspector → Defect
# ---------------------------------------------------------------------------


class Defect(BaseModel):
    """One detected defect candidate within a tile."""

    defect_id: UUID = Field(default_factory=uuid4)
    tile_id: UUID
    defect_class: DefectClass
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["labeled_detector", "anomaly_arm"] = Field(
        description=(
            "labeled_detector for the 6 DeepPCB classes, anomaly_arm for the "
            "4 anomaly-detected classes"
        )
    )
    raw_model_output: dict[str, Any] | None = Field(
        default=None,
        description="Original Gemini response payload, opaque to downstream agents",
    )


# ---------------------------------------------------------------------------
# FMEA Risk → FMEAEntry
# ---------------------------------------------------------------------------


class FMEAEntry(BaseModel):
    """FMEA mapping for one defect."""

    defect_id: UUID
    severity: Severity
    default_action: ActionKind
    justification: str = Field(
        description="One-paragraph reasoning, shown to operator and stored in evidence"
    )
    escalate_to_senior: bool = Field(
        default=False,
        description="Set True when taxonomy flags 'always escalate'",
    )


# ---------------------------------------------------------------------------
# Supervisor → Action
# ---------------------------------------------------------------------------


class Action(BaseModel):
    """Supervisor's final per-tile decision."""

    tile_id: UUID
    kind: ActionKind
    reason: str = Field(description="Short rationale shown in UI")
    triggered_hitl: bool = Field(
        default=False,
        description=(
            "True when this action requires explicit operator decision "
            "(kind == HUMAN_REVIEW or escalate_to_senior)"
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Aggregated confidence across defects in this tile " "(max of per-defect confidences)"
        ),
    )


# ---------------------------------------------------------------------------
# Operator response
# ---------------------------------------------------------------------------


class OperatorResponse(BaseModel):
    """Operator's decision after reviewing the agent recommendation."""

    tile_id: UUID
    operator_id: str
    action: OperatorAction
    final_kind: ActionKind = Field(
        description=(
            "The action ultimately recorded. Equals agent kind if accept; "
            "operator's chosen kind if override."
        )
    )
    rationale: str | None = Field(
        default=None,
        description="Required when action == OVERRIDE",
    )
    responded_at: datetime


# ---------------------------------------------------------------------------
# Evidence Report → TileReport, QCReport, LotSummary
# ---------------------------------------------------------------------------


class TileReport(BaseModel):
    """Immutable per-tile evidence record."""

    tile: Tile
    defects: list[Defect]
    fmea_entries: list[FMEAEntry]
    agent_action: Action
    operator_response: OperatorResponse | None = Field(
        default=None,
        description="Populated once the operator accepts or overrides",
    )
    finalized_at: datetime | None = None


class QCReport(BaseModel):
    """Board-level aggregated evidence record."""

    report_id: UUID = Field(default_factory=uuid4)
    board_id: str
    lot_id: str
    operator_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: BoardStatus
    tile_reports: list[TileReport]
    defect_histogram: dict[DefectClass, int] = Field(default_factory=dict)
    senior_escalations: list[UUID] = Field(
        default_factory=list,
        description="tile_ids that required senior escalation",
    )
    operator_signoff_at: datetime | None = None


class LotSummary(BaseModel):
    """Lot-level rollup across all QCReports in the lot."""

    lot_id: str
    boards: list[str]  # board_ids
    pass_count: int = 0
    rework_count: int = 0
    hold_count: int = 0
    status: LotStatus
    finalized_at: datetime | None = None


__all__ = [
    "DefectClass",
    "Severity",
    "ActionKind",
    "OperatorAction",
    "BoardStatus",
    "LotStatus",
    "BBox",
    "TilePosition",
    "Tile",
    "Defect",
    "FMEAEntry",
    "Action",
    "OperatorResponse",
    "TileReport",
    "QCReport",
    "LotSummary",
]
