"""
Pydantic v2 schemas for the Claude Fable 5 reasoning service.

Input models describe display-defect observations coming from the
Neuron Vision inspectors; output models are enforced server-side via the
Anthropic structured-outputs feature (``output_config.format``) and
re-validated client-side with Pydantic.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request models (our side — never sent as an LLM schema)
# ---------------------------------------------------------------------------


class DefectObservation(BaseModel):
    """One defect found by the vision pipeline on a display unit."""

    defect_type: str = Field(
        description="Defect class, e.g. 'dead_pixel_cluster', 'mura', 'line_defect'"
    )
    location: str = Field(
        description="Panel zone or coordinates, e.g. 'upper-left quadrant', 'x=512,y=80'"
    )
    severity: Literal["minor", "moderate", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    details: str = Field(default="", description="Free-form inspector notes")


class ProcessContext(BaseModel):
    """Manufacturing context that helps Fable 5 reason about causes."""

    line_id: str = Field(default="", description="Production line identifier")
    product: str = Field(default="", description="Panel / display model under inspection")
    stage: str = Field(default="", description="Process stage, e.g. 'cell', 'module', 'final QC'")
    recent_changes: list[str] = Field(
        default_factory=list,
        description="Recent process changes: material lots, recipe edits, maintenance events",
    )
    environment: str = Field(
        default="", description="Relevant environment notes (temp, humidity, ESD)"
    )
    defect_history: str = Field(default="", description="Short summary of recent defect trends")


class DefectAnalysisRequest(BaseModel):
    """Payload for the /analyze-defect endpoint."""

    defects: list[DefectObservation] = Field(min_length=1)
    context: ProcessContext | None = None
    question: str = Field(
        default="",
        description="Optional focused question from the QC engineer",
    )


# ---------------------------------------------------------------------------
# Structured-output models (sent to the API as JSON schema)
#
# Numeric range constraints (ge/le) are stripped from the wire schema by the
# client (the structured-outputs API rejects them) and enforced here on
# validation instead.
# ---------------------------------------------------------------------------


class CausalFactor(BaseModel):
    """One contributing factor in the causal analysis."""

    factor: str = Field(description="Short name of the factor")
    mechanism: str = Field(
        description="Physical/process mechanism linking the factor to the defect"
    )
    likelihood: Literal["low", "medium", "high"]
    evidence: list[str] = Field(description="Observations supporting this factor")


class RootCauseAnalysis(BaseModel):
    """Causal reasoning result for a defect set."""

    primary_root_cause: str = Field(description="Single most likely root cause")
    causal_chain: list[str] = Field(description="Ordered chain from root cause to observed defect")
    contributing_factors: list[CausalFactor]
    ruled_out: list[str] = Field(
        description="Hypotheses considered and rejected, with one-line reason"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class Recommendation(BaseModel):
    """One actionable recommendation for QC / process engineers."""

    action: str = Field(description="Concrete action to take")
    rationale: str = Field(description="Why this action addresses the cause")
    priority: Literal["immediate", "short_term", "long_term"]
    owner_hint: str = Field(description="Suggested owner, e.g. 'process engineer', 'maintenance'")
    expected_impact: str = Field(description="Expected effect on defect rate or risk")


class RecommendationSet(BaseModel):
    """Recommendations produced for a defect set."""

    recommendations: list[Recommendation]
    quick_wins: list[str] = Field(description="Actions doable within one shift")
    summary: str


class DefectReasoning(BaseModel):
    """Full reasoning result: explanation + root cause + recommendations."""

    summary: str = Field(description="2-4 sentence engineer-facing explanation of what is going on")
    root_cause: RootCauseAnalysis
    recommendations: list[Recommendation]


# ---------------------------------------------------------------------------
# Call metadata + response envelopes (our side)
# ---------------------------------------------------------------------------


class Fable5CallMeta(BaseModel):
    """Observability metadata attached to every reasoning response."""

    model_id: str
    fallback_used: bool = False
    fallback_reason: str = ""
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    cached: bool = False


class DefectReasoningResponse(BaseModel):
    """Envelope returned by /analyze-defect."""

    result: DefectReasoning
    meta: Fable5CallMeta


class RootCauseResponse(BaseModel):
    """Envelope returned by /root-cause."""

    result: RootCauseAnalysis
    meta: Fable5CallMeta


class RecommendationsResponse(BaseModel):
    """Envelope returned by /recommendations."""

    result: RecommendationSet
    meta: Fable5CallMeta
