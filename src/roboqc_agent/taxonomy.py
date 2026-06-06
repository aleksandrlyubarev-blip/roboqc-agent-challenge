"""Canonical SMT defect taxonomy, encoded from ``docs/fmea_taxonomy.md``.

This is the single in-code source of truth for the severity, default action,
detection source, and senior-escalation flag of each of the ten frozen defect
classes. The FMEA Risk prompt, the offline demo provider, and any deterministic
fallback all read from here so they cannot drift from the frozen taxonomy doc.

Frozen 2026-05-16 alongside ``docs/fmea_taxonomy.md`` and ``schemas.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from roboqc_agent.schemas import ActionKind, DefectClass, Severity

DefectSource = Literal["labeled_detector", "anomaly_arm"]


@dataclass(frozen=True, slots=True)
class TaxonomyEntry:
    """Frozen taxonomy facts for one defect class."""

    severity: Severity
    default_action: ActionKind
    source: DefectSource
    always_escalate: bool = False


TAXONOMY: dict[DefectClass, TaxonomyEntry] = {
    DefectClass.OPEN_TRACE: TaxonomyEntry(Severity.CRITICAL, ActionKind.HOLD, "labeled_detector"),
    DefectClass.SHORT_CIRCUIT: TaxonomyEntry(
        Severity.CRITICAL, ActionKind.HOLD, "labeled_detector"
    ),
    DefectClass.MOUSEBITE: TaxonomyEntry(Severity.MAJOR, ActionKind.REWORK, "labeled_detector"),
    DefectClass.SPUR: TaxonomyEntry(Severity.MINOR, ActionKind.PASS, "labeled_detector"),
    DefectClass.EXCESS_COPPER: TaxonomyEntry(Severity.MAJOR, ActionKind.REWORK, "labeled_detector"),
    DefectClass.PINHOLE: TaxonomyEntry(Severity.MINOR, ActionKind.PASS, "labeled_detector"),
    DefectClass.TOMBSTONING: TaxonomyEntry(
        Severity.CRITICAL, ActionKind.HOLD, "anomaly_arm", always_escalate=True
    ),
    DefectClass.SOLDER_BRIDGE: TaxonomyEntry(Severity.CRITICAL, ActionKind.HOLD, "anomaly_arm"),
    DefectClass.INSUFFICIENT_SOLDER: TaxonomyEntry(
        Severity.MAJOR, ActionKind.REWORK, "anomaly_arm"
    ),
    DefectClass.MISSING_COMPONENT: TaxonomyEntry(Severity.CRITICAL, ActionKind.HOLD, "anomaly_arm"),
}


def taxonomy_table() -> str:
    """Render the taxonomy as a compact text table for agent system prompts."""

    rows = [
        f"- {cls.value}: severity={entry.severity.value}, "
        f"default_action={entry.default_action.value}, source={entry.source}"
        + (", always_escalate_to_senior=true" if entry.always_escalate else "")
        for cls, entry in TAXONOMY.items()
    ]
    return "\n".join(rows)


__all__ = ["DefectSource", "TaxonomyEntry", "TAXONOMY", "taxonomy_table"]
