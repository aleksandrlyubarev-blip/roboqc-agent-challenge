# Architecture — RoboQC Agent

> **Current submission note:** this document captures the earlier 4-agent ADK/API
> scaffold under `src/roboqc_agent`. The live hackathon submission and Cloud Run
> UI use the 5-agent `src/neuron_vision` runtime described in the README and
> demo package: Triage -> Solder / Component / Marking inspectors in parallel
> -> Chief Inspector. Keep this file for scaffold context, not as the primary
> video/Devpost architecture.

**Status:** active, week-1 deliverable per `codex_brief.md`.
**Scope:** describes how the four ADK agents are decomposed, wired, and
deployed for the Google for Startups AI Agents Challenge submission. Source of
truth for Codex implementation under `src/roboqc_agent/`.
**Frozen reference docs:** `inspection_target_spec.md`, `fmea_taxonomy.md`,
`operator_workflow.md`, `non_negotiables.md`, `schemas.py`.

---

## 1. System view

```
┌──────────────────────── Streamlit UI (ui/streamlit_app.py) ─────────────────┐
│  - tile capture (file upload, future microscope SDK)                        │
│  - per-tile review surface                                                  │
│  - board / lot rollup                                                       │
│  - operator override + rationale capture                                    │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │ HTTP, JSON (Tile + image_uri reference)
┌──────────────────▼────────── Cloud Run service ─────────────────────────────┐
│  graph.py          ADK graph wiring                                         │
│   ├── Vision Inspector  (Gemini multimodal)   ──► Defect[]                  │
│   ├── FMEA Risk         (Gemini text)         ──► FMEAEntry[]               │
│   ├── Evidence Report   (text + storage)      ──► TileReport / QCReport     │
│   └── Supervisor        (text + policy)       ──► Action                    │
│                                                                             │
│  Cross-cutting:                                                             │
│   - providers/vertex_gemini.py    (Vertex AI client, structured output)     │
│   - tools/base.py                 (generic typed-tool contract)             │
│   - orchestration/tool_runner.py  (ADK invocation pattern)                  │
│   - execution_store/              (SQLite QCReport + event persistence)     │
│   - policy/                       (friction policy → ActionKind)            │
│   - hitl/                         (conformal calibration, post-MVP)         │
│   - telemetry/, auth/, checkpointing/                                       │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
              Planned image object storage + SQLite (current repo)
              image_uri references, QCReport, execution events
```

Single Cloud Run service, single Streamlit frontend, single Vertex provider.
No second backend. No MCP server in this surface (anti-scope from
`non_negotiables.md`).

---

## 2. Four agents — boundaries and contracts

The four-agent decomposition is non-negotiable for the submission
(`non_negotiables.md` §4). Each agent has one job, one input shape, one
output shape. All inter-agent communication goes through the Pydantic
contracts in `schemas.py`.

### 2.1 Vision Inspector

- **Role:** ingest a single microscope tile, return defect candidates.
- **Input:** `Tile` (from `schemas.py`).
- **Output:** `list[Defect]`. Empty list is a valid "clean tile" signal.
- **Model:** Vertex AI Gemini 2.5 Pro, multimodal call (`generate_multimodal`
  in `providers/vertex_gemini.py`). Structured output via
  Pydantic `response_schema = list[Defect]`.
- **Two-source rule:** the agent emits defects with
  `source = "labeled_detector"` for the six DeepPCB-style classes
  (open / short / mousebite / spur / excess_copper / pinhole) and
  `source = "anomaly_arm"` for the four anomaly-detected classes
  (tombstoning / solder_bridge / insufficient_solder / missing_component).
  See `fmea_taxonomy.md` for the canonical class list. The agent's system
  prompt enumerates the classes and instructs the model to return at most one
  defect per spatial region; deduplication is the agent's responsibility, not
  the downstream agents'.
- **Confidence model:** raw model output is normalized to `[0.0, 1.0]` before
  returning. Below-floor confidences (`< 0.50` after normalization) are
  dropped at the Vision Inspector boundary — they create noise downstream and
  the operator does not want false-positive overload.
- **What the Vision Inspector does NOT do:** severity assignment, action
  selection, evidence persistence, HITL routing. All four are downstream
  responsibilities.

### 2.2 FMEA Risk

- **Role:** map each detected defect to severity, default action, and
  justification text.
- **Input:** `list[Defect]` from a single tile.
- **Output:** `list[FMEAEntry]`, one per defect.
- **Model:** Vertex AI Gemini 2.5 Pro, **text-only**. No image is passed
  here — the image was already processed by Vision Inspector. Text-only
  keeps cost down and avoids retokenizing the tile.
- **Knowledge base:** the system prompt embeds the severity table and
  HITL triggers from `fmea_taxonomy.md`. The agent must produce
  `severity`, `default_action`, `justification`, and `escalate_to_senior`
  consistent with the taxonomy. The `justification` field is shown to the
  operator verbatim and stored in the evidence record — therefore it must
  be operator-readable, not internal reasoning.
- **Determinism note:** because the input is text-only and the taxonomy is
  small, this agent is the most predictable of the four. Codex should
  consider a deterministic fallback (lookup table) when confidence on the
  upstream `Defect` is high — this is a P1 optimization, not a v1 requirement.

### 2.3 Evidence Report

- **Role:** assemble per-tile evidence records, then aggregate to board
  (`QCReport`) and lot (`LotSummary`).
- **Input (tile-level):** `Tile`, `list[Defect]`, `list[FMEAEntry]`,
  `Action`, optional `OperatorResponse`.
- **Output:** `TileReport` (per tile), `QCReport` (per board, append-only),
  `LotSummary` (per lot).
- **Model:** primarily code, not an LLM agent in the strict sense. Two paths:
  - **Tile-level:** pure aggregation — no LLM call required. The Evidence
    Report agent assembles the `TileReport` from upstream outputs and writes
    to the Execution Store.
  - **Board-level summary text:** one optional Gemini text call to produce
    the human-readable board summary shown on the Streamlit rollup screen.
    This is the only LLM surface in Evidence Report.
- **Immutability rule:** once `operator_signoff_at` is set on a `QCReport`,
  the report is treated as append-only. Subsequent corrections must be new
  records with an explicit reference to the original (audit trail).
- **What it does NOT do:** make pass/rework/hold decisions. That's Supervisor.
  Decide HITL routing. That's Supervisor. Talk to the operator. That's the UI.

### 2.4 Supervisor

- **Role:** issue the final per-tile `Action` and gate HITL.
- **Input:** `list[Defect]` + `list[FMEAEntry]` for one tile.
- **Output:** one `Action`.
- **Model:** Vertex AI Gemini 2.5 Pro, text-only — but the decision is mostly
  rule-based and the model is a thin wrapper for short rationale text.
- **Decision rule (deterministic core):**
  1. Aggregate tile confidence = `max(defect.confidence for defect in defects)`,
     or `1.0` if no defects (clean tile, full confidence in cleanness only if
     the Vision Inspector also returned `[]` with no model uncertainty
     signal).
  2. Action selection:
     - any FMEA entry with `severity == CRITICAL` → `HOLD`
     - else any FMEA entry with `severity == MAJOR` → `REWORK`
     - else if all entries are `MINOR` → `PASS`
     - clean tile (no defects) → `PASS`
  3. HITL override:
     - aggregate confidence `< 0.80` → force `HUMAN_REVIEW`,
       `triggered_hitl = True`
     - any FMEA entry with `escalate_to_senior == True` →
       `triggered_hitl = True` (keep the deterministic action but flag)
     - taxonomy-specific triggers from `fmea_taxonomy.md` §"HITL trigger"
       fields are encoded in the policy engine; see §6 below.
- **What the LLM provides:** the `reason` string shown in the UI. Keep
  short — UI column has limited space. Two-sentence target.
- **What the Supervisor does NOT do:** classify defects, write evidence,
  call Vision Inspector. Single-purpose decision node.

### 2.5 Why exactly four — not three, not five

Three would collapse FMEA Risk into Supervisor; this is reasonable for
production but for the submission we keep them separate because (a) the
demo video is cleaner when each agent has one job on screen, (b) FMEA Risk
output is independently testable and FMEA-taxonomy-aligned, (c) the
deterministic-fallback optimization in §2.2 only makes sense when FMEA Risk
is a separately-bounded module.

Five would split Vision Inspector into "labeled detector" and "anomaly arm"
agents. We don't — both are Gemini multimodal calls with different system
prompts; one agent with two prompt branches is simpler than two agents with
identical infrastructure.

This decomposition is frozen per `non_negotiables.md` §4 until 2026-06-06.

---

## 3. Data flow per tile

```
Tile (Streamlit upload → Cloud Run endpoint)
  │
  ├─► image_uri assigned
  │
  ▼
Vision Inspector (Gemini multimodal)
  │
  ├─► list[Defect]    # confidence-floored, deduplicated
  │
  ▼
FMEA Risk (Gemini text)
  │
  ├─► list[FMEAEntry] # one per Defect, severity + default_action + reason
  │
  ▼
Supervisor (rule-based core + Gemini for reason text)
  │
  ├─► Action          # final per-tile decision, HITL flag
  │
  ▼
Evidence Report (code, optional Gemini for summary)
  │
  ├─► TileReport      # persisted to ExecutionStore
  │
  ▼
UI surfaces Action + Defect overlays to operator
  │
  ▼
Operator review → OperatorResponse
  │
  ├─► finalize TileReport (append OperatorResponse, set finalized_at)
  │
  ▼
ExecutionStore: tile record immutable, audit-grade
```

A clean tile (no defects) short-circuits FMEA Risk (no entries to map) and
goes directly through Supervisor with `kind = PASS`, `confidence = 1.0`,
`triggered_hitl = False`. Evidence Report still persists the clean record —
the audit trail covers all tiles, not only defective ones.

End-to-end latency target per tile: ≤ 8 s (`operator_workflow.md` §5).
Per-call budget allocation:

| Step | Budget |
|---|---|
| Vision Inspector (multimodal) | 4 s |
| FMEA Risk (text, batched defects) | 1.5 s |
| Supervisor (text, short rationale) | 1 s |
| Evidence Report (storage write) | 0.5 s |
| Overhead (graph, serialization, network) | 1 s |

If Vision Inspector consistently exceeds 4 s, the right fix is image
preprocessing (downscale to 1024 px on long side, JPEG quality 85) before
the call, not switching models.

---

## 4. Aggregation — tile → board → lot

Per `operator_workflow.md`:

- **Board (`QCReport`):**
  - Status derives deterministically from tile statuses:
    `any HOLD → board.status = COMPLETE_HOLD`,
    else `any REWORK → COMPLETE_REWORK`, else `COMPLETE_PASS`.
  - `defect_histogram` counts `DefectClass` occurrences across all tile
    reports.
  - `senior_escalations` lists `tile_id` of tiles where
    `Action.triggered_hitl == True` AND
    `OperatorResponse` indicates senior escalation needed.
  - Operator sign-off (`operator_signoff_at`) closes the board.

- **Lot (`LotSummary`):**
  - Status derives from board counts:
    `hold_count / total_boards > 0.10` → `HOLD_FOR_ENGINEERING`.
  - Otherwise `APPROVED` after all boards are signed off.
  - No LLM call. Pure code.

Aggregation lives inside Evidence Report agent. The graph triggers
board-level aggregation when the operator marks the board complete in the
UI, and triggers lot aggregation when all boards in a lot are signed off.

---

## 5. ADK graph wiring (`graph.py`)

The ADK graph has two distinct flows:

### 5.1 Tile flow (per Streamlit "Capture tile")

Sequential composition with structured outputs at each step. Pseudo-ADK:

```
tile_graph = ADKGraph()
tile_graph.add(VisionInspectorAgent, output_key="defects")
tile_graph.add(FMEARiskAgent, output_key="fmea_entries",
               input_keys=["defects"])
tile_graph.add(SupervisorAgent, output_key="action",
               input_keys=["defects", "fmea_entries"])
tile_graph.add(EvidenceReportAgent.persist_tile,
               input_keys=["tile", "defects", "fmea_entries", "action"])
```

No branching, no retry loops, no LangGraph. Sequential is correct for the
submission — the failure mode is per-step error, surfaced via FastAPI HTTP
status, not in-graph retry.

### 5.2 Board / lot flow (triggered from UI, not per-tile)

Two separate entry points on the Cloud Run service:

```
POST /api/boards/{board_id}/finalize
  └─► EvidenceReportAgent.aggregate_board → QCReport finalized

POST /api/lots/{lot_id}/finalize
  └─► EvidenceReportAgent.aggregate_lot → LotSummary finalized
```

These are not part of the per-tile graph. Keeping them out simplifies the
ADK graph and matches the operator's mental model: aggregation happens at
explicit "I'm done with this board / lot" actions, not implicitly per tile.

---

## 6. HITL architecture

HITL is not a separate agent. It is encoded in two places:

1. **Supervisor's decision rule (§2.4)** — the only place that emits
   `kind = HUMAN_REVIEW` or sets `triggered_hitl = True`.
2. **`policy/` module** — friction-policy donor adapted from prior work.
   Input: `(defect_class, severity, confidence)`. Output: `ActionKind` or
   `human_review` override. The policy module is the canonical place to
   adjust HITL behavior without modifying agent code.

Supervisor calls `policy.evaluate(defect_class, severity, confidence)` for
each FMEAEntry, then aggregates. The default policy mirrors §2.4 above. The
conformal-calibration HITL donor (P2, `hitl/`) refines confidence thresholds
post-MVP — it is not in the v1 submission scope.

Four HITL levels from `operator_workflow.md` map to architecture as follows:

| Workflow level | Architectural realization |
|---|---|
| Tile, confidence < 0.80 | Supervisor decision rule, `kind = HUMAN_REVIEW` |
| Tile, "always escalate" defect class | FMEA Risk sets `escalate_to_senior = True`; Supervisor sets `triggered_hitl = True` |
| Board, any tile with HOLD | UI gate — operator must confirm before closing board |
| Lot, hold rate > 10% | LotSummary deterministic status |

The operator's override is recorded in `OperatorResponse.rationale` (free
text, required when `action == OVERRIDE`) and persisted in `TileReport`.

---

## 7. Storage — ExecutionStore

Single storage layer for inspection evidence.

- **Current v1 implementation:** `execution_store/sqlite_repo.py` persists
  board-level `QCReport` records plus append-only execution events. This is the
  committed baseline that runs locally today.
- **Planned image persistence:** `Tile.image_uri` already models an external
  image reference, but the repo does not yet commit a concrete object-storage
  adapter. GCS remains the intended Cloud Run deployment direction, not a
  completed v1 module.
- **Expected extension during agent implementation:** tile-level evidence and
  lot-level aggregation should be added behind the same execution-store
  boundary once the corresponding agents are implemented.
- **Post-submission durable backend:** intentionally not selected yet. The
  public architecture should not claim Firestore, SQL, or another service
  before the v1 flow proves what durability shape is actually needed.

The current schema is SMT-inspection-specific, not a generic execution trace.
The execution-store donor from prior work supplied useful storage patterns; the
repo's committed implementation is intentionally narrower than the eventual
evidence model until more of the agent flow exists.

Immutability: append-only after `operator_signoff_at` is set. Updates after
sign-off must be new records with `references_record_id` (currently informal;
formalize in schema v1.1 if needed before deadline).

---

## 8. Provider — Vertex AI Gemini

Single provider module: `providers/vertex_gemini.py`. Current public methods:

```python
generate_text(
    prompt: str,
    response_schema: type[BaseModel] | dict[str, Any] | None = None,
) -> GenerationResult

generate_multimodal(
    images: Sequence[str | Path],
    prompt: str,
    response_schema: type[BaseModel] | dict[str, Any] | None = None,
) -> GenerationResult
```

Auth via Application Default Credentials. Region `us-central1`. Model
`gemini-2.5-pro` for all four agents in v1 — no per-agent model selection
in the submission scope. If a per-agent model selection is needed later
(e.g., Flash for FMEA Risk to cut cost), that lives in the provider's
config, not the agent code.

Structured output uses the Gemini `response_schema` parameter. The provider
returns a `GenerationResult` wrapper with:

- `parsed` — structured output when available
- `text` — provider text response
- `raw` — original SDK response for telemetry / debugging

Agent code should consume `parsed` for structured flows and should not parse raw
JSON itself.

Telemetry hooks (P1, `telemetry/`) wrap every provider call with token
counts, latency, and request_id. This is the boundary at which Cloud Run
monitoring captures LLM latency and error rate. Cost monitoring is deferred
until the provider surface exposes a trustworthy normalized cost field rather
than an inferred estimate.

---

## 9. Deployment — Cloud Run

Single service, single container. Region `us-central1` (matches Vertex AI
region — no cross-region egress for Gemini calls).

- **Container:** Python 3.11, ADK + Vertex AI SDK + Pydantic 2.x + Streamlit
  + FastAPI. Streamlit served separately or as a thin front in front of the
  FastAPI graph endpoint — Codex decides on the simplest packaging at deploy
  time.
- **Auth:** Cloud Run IAM, service account with Vertex AI User role, GCS
  Object Admin scoped to the inspection-images bucket. No public IAM.
- **Secrets:** none in v1. ADC handles credentials. No API keys committed.
- **Concurrency:** 1 request per instance during the demo (avoids Gemini
  rate-limit interaction across concurrent tile calls). Autoscale 0-10.

Deploy artifacts under `infra/cloudrun/`. One-shot deploy script verified
on a dummy endpoint as week-1 deliverable per `codex_brief.md` §7.

---

## 10. Frontend — Streamlit

Single-file Streamlit app at `ui/streamlit_app.py`. Surfaces:

1. **Session setup** — board model, lot ID, magnification, tile grid.
2. **Tile capture loop** — upload image, see agent annotations overlaid,
   accept/override + optional rationale, next tile.
3. **Board rollup** — heatmap (tile grid colored by status), defect
   histogram, board action recommendation, sign-off button.
4. **Lot rollup** — board roster, pass/rework/hold counts, lot action.

The four-agent decomposition is invisible to the operator. UI presents one
"RoboQC" entity with one decision per tile. Internal confidence is shown as
a color indicator (green / yellow / red), not a number.

No second frontend. No Gradio, no custom React, no FastAPI Swagger as a
user surface. Streamlit only.

---

## 11. Telemetry, auth, checkpointing

These are P1 donor migrations from prior deploy work. They are not on the
per-request critical path of the submission demo, but they are required for
the Cloud Run deployment to be production-shaped:

- **`telemetry/`:** wraps every Gemini call, records token counts, latency,
  request_id. Surfaces in Cloud Run monitoring + Cloud Logging.
- **`auth/`:** Cloud Run IAM + service account. Simplified from the donor —
  no OAuth flows, no per-user auth in the submission demo (single-operator
  context).
- **`checkpointing/`:** reserved for an ADK-native persistence strategy. The
  donor implementation from earlier work is LangGraph-specific and is not
  transplanted directly into this repo. It is not on the v1 demo critical path;
  the implementation shape should be chosen only once the ADK graph wiring is
  in place.

---

## 12. Anti-scope (architectural)

Per `non_negotiables.md` §"Frozen anti-scope" — restated here in
architectural terms so PRs are reviewable against this doc:

- No second frontend, no FastAPI as a user-facing surface.
- No LangGraph, no LiteLLM, no ROMA — ADK is the only orchestration.
- No MCP server in the submission deploy.
- No domain narrative outside SMT first-article PCB inspection.
- No generative media pipelines inside the repo.
- No more than four agents until 2026-06-06.

A PR that drifts outside these constraints is rejected at review regardless
of how good the code is.

---

## 13. Open architectural questions

These are for Codex to decide during P1 implementation. They do not require
founder input under the AI Collaboration Protocol (`ai_collaboration_protocol.md`).
If a decision changes product scope, escalate via `open_questions.md`.

1. **Vision Inspector — two prompts or one?** Single Gemini call with a
   system prompt covering all 10 classes, vs. two parallel calls (labeled
   detector + anomaly arm) merged in agent code. Recommended default: one
   call, one prompt — cost is half, latency is half. Revisit if defect
   recall on anomaly classes underperforms in benchmark.
2. **FMEA Risk batching.** One Gemini call per tile (all defects in one
   prompt) vs. one call per defect. Recommended: per-tile batch — defects
   in one tile share context. Per-defect only if the batched JSON output
   degrades quality.
3. **Supervisor reason-text generation.** Use Gemini for the `reason` field,
   or generate deterministically from the FMEA justification. Recommended:
   deterministic concatenation for v1 — saves a Gemini call per tile (≈ 1 s
   end-to-end latency), and the reason is genuinely templatable.
4. **ExecutionStore concurrency.** SQLite for v1 is single-writer. If the
   demo includes a multi-operator scenario, this breaks. Recommended: stay
   single-operator for the submission demo; document the limitation in
   `demo.md`.
5. **Provider retry policy.** Vertex AI returns 429 on rate-limit and 5xx on
   transient errors. Recommended: one retry with exponential backoff (1 s,
   3 s) at the provider level; surface failure to the agent and to the UI
   if both attempts fail. No retry inside agent code — keep retries in one
   place.

These are Codex decisions per the AI Collaboration Protocol §"Default
decision rule". Record outcomes in `decision_log.md`.

---

## Document hygiene

This document is the architectural contract for v1 submission. Material
changes to:

- agent count or boundaries,
- inter-agent message shapes,
- provider selection,
- HITL gate logic,
- storage schema,

require a `decision_log.md` entry. Cosmetic edits (clarification, typo,
example) do not.

End-of-week-2 deliverable `docs/demo.md` walks through this architecture
from the operator's perspective with a concrete board example.
