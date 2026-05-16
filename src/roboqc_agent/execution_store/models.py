"""Execution timeline models for RoboQC evidence persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class ExecutionEvent:
    """Append-only event emitted during report assembly."""

    report_id: UUID
    event: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now)
