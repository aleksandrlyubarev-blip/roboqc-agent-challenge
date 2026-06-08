"""
Pydantic v2 schemas for all Neuron Vision Display agents.
All outputs are strictly typed — zero dicts, zero Any.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Triage Agent
# ---------------------------------------------------------------------------

class TriageResult(BaseModel):
    """Fast first-pass assessment of the PCB image."""
    board_type: str = Field(description="PCB board type, e.g. 'double-layer SMT', 'single-layer through-hole'")
    risk_zones: list[str] = Field(description="Areas requiring close inspection, e.g. ['BGA clusters', 'fine-pitch IC']")
    inspection_priority: Literal["low", "medium", "high", "critical"] = Field(
        description="Overall inspection urgency"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    notes: str = Field(default="", description="Any additional triage observations")


# ---------------------------------------------------------------------------
# Solder Inspector
# ---------------------------------------------------------------------------

class SolderDefect(BaseModel):
    defect_type: Literal[
        "cold_joint", "solder_bridge", "insufficient_solder",
        "excess_solder", "tombstoning", "lifted_pad", "void"
    ]
    location: str = Field(description="Component reference or board region, e.g. 'U4 pin 3'")
    severity: Literal["minor", "moderate", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)


class SolderReport(BaseModel):
    """Solder quality inspection result."""
    defects: list[SolderDefect] = Field(default_factory=list)
    overall_solder_quality: Literal["acceptable", "marginal", "reject"]
    inspected_joints_estimate: int = Field(ge=0, description="Estimated number of joints inspected")
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


# ---------------------------------------------------------------------------
# Component Inspector
# ---------------------------------------------------------------------------

class ComponentIssue(BaseModel):
    component_ref: str = Field(description="Reference designator, e.g. 'C12', 'U3'")
    issue_type: Literal["missing", "wrong_value", "misoriented", "shifted", "tombstoned", "damaged"]
    severity: Literal["minor", "moderate", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    details: str = Field(default="")


class ComponentReport(BaseModel):
    """Component placement and presence inspection result."""
    issues: list[ComponentIssue] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list, description="Component refs confirmed missing")
    misoriented: list[str] = Field(default_factory=list, description="Component refs with wrong orientation")
    shifted: list[str] = Field(default_factory=list, description="Component refs with placement shift")
    overall_placement_quality: Literal["acceptable", "marginal", "reject"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


# ---------------------------------------------------------------------------
# Marking & Labeling Inspector
# ---------------------------------------------------------------------------

class MarkingIssue(BaseModel):
    area: str = Field(description="Board area or component ref where marking issue found")
    issue_type: Literal["illegible", "missing", "damaged", "incorrect_polarity_mark", "qr_unreadable"]
    severity: Literal["minor", "moderate", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)


class MarkingReport(BaseModel):
    """Silkscreen, QR code, and labeling inspection result."""
    issues: list[MarkingIssue] = Field(default_factory=list)
    unreadable: list[str] = Field(default_factory=list, description="Text areas that are unreadable")
    missing_marks: list[str] = Field(default_factory=list, description="Expected marks that are absent")
    qr_valid: bool = Field(description="True if QR/barcode is present and readable")
    overall_marking_quality: Literal["acceptable", "marginal", "reject"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


# ---------------------------------------------------------------------------
# Chief Inspector (Reasoning Agent)
# ---------------------------------------------------------------------------

class EvidenceEntry(BaseModel):
    source_agent: Literal["triage", "solder_inspector", "component_inspector", "marking_inspector"]
    finding: str
    severity: Literal["info", "minor", "moderate", "critical"]


class QCVerdict(BaseModel):
    """Final QC decision from the Chief Inspector."""
    status: Literal["pass", "rework", "hold", "human_review"]
    evidence_log: list[EvidenceEntry] = Field(default_factory=list)
    critical_findings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(description="Human-readable QC summary for the operator")
    recommended_actions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Full pipeline result (Streamlit display model)
# ---------------------------------------------------------------------------

class PipelineResult(BaseModel):
    """Complete result from the 5-agent QC brigade."""
    triage: TriageResult
    solder: SolderReport
    components: ComponentReport
    markings: MarkingReport
    verdict: QCVerdict
    duration_seconds: float = Field(ge=0.0)
