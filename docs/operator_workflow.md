# Operator Workflow — RoboQC Agent for SMT First-Article Inspection

**Status:** FROZEN for Google submission, 2026-05-16.
**Scope:** Describes the end-to-end interaction between the QC technician and the agent during a first-article inspection session. Source of truth for Streamlit UI design and for system-prompt context of all four agents.

---

## 1. Roles

- **Operator (junior QC technician):** captures tiles, reviews agent decisions, performs rework or escalation. Primary user.
- **Agent (RoboQC):** processes each tile, classifies defects, recommends action. Always advisory; never autonomous.
- **Senior QC (escalation target):** receives HITL escalations from the agent. Out of scope for the demo MVP — escalations are logged but no separate senior UI.

## 2. Session lifecycle

### Phase 1 — Setup

1. Operator creates a new inspection session in the UI:
   - Board model (selected from library or new entry).
   - Lot ID / serial range.
   - Microscope magnification setting (5×, 10×, 20×, 40×).
   - Tile grid (default 20 × 30, configurable).
2. System creates a fresh `QCReport` record in the Execution Store with status `in_progress`.

### Phase 2 — Tile capture loop

For each tile position (row, col) in the grid:

1. Operator positions board under microscope at tile (row, col).
2. Operator captures image (UI: "Capture tile" button or hotkey).
3. UI uploads tile to agent endpoint with metadata.
4. **Vision Inspector Agent** processes the tile, returns a list of `Defect` candidates with class, bounding box, and confidence.
5. **FMEA Risk Agent** maps each defect to severity and recommended action per `fmea_taxonomy.md`.
6. **Supervisor Agent** issues a tile-level decision: `pass | rework | hold | human_review`.
7. UI displays the tile with overlaid defect annotations and the recommended action.
8. Operator reviews:
   - If agent says `pass` and operator agrees → click Next, move to next tile.
   - If agent says `rework` → operator marks tile for rework, optionally adds note, Next.
   - If agent says `hold` → operator confirms hold; the entire board is flagged.
   - If agent says `human_review` → operator must make a decision (pass / rework / hold) and provide rationale text. The override is recorded.
9. **Evidence Report Agent** writes the tile-level evidence record to the Execution Store.

### Phase 3 — Board completion

When all tiles are processed (or operator marks the board complete early):

1. Evidence Report Agent aggregates tile records into a board-level `QCReport`.
2. Supervisor Agent issues a board-level decision based on tile decisions:
   - Any `hold` tile → board status `hold`.
   - Any `rework` tile, no `hold` → board status `rework`.
   - All tiles `pass` → board status `pass`.
3. UI shows board summary: tile heatmap, defect histogram, action recommendation.
4. Operator signs off (clicks "Approve" or "Override"); session moves to `complete` with operator signature attached.

### Phase 4 — Lot completion

Sessions are grouped by lot. When all boards in a lot are processed:

- UI shows lot-level rollup: how many boards passed, reworked, held.
- If `hold` rate > threshold (default 10%) → lot status `hold_for_engineering_review`. This is the recommended-but-not-enforced gate that prevents passing a problematic lot.

---

## 3. HITL gates — explicit

HITL is built into the workflow at four levels:

| Level | Trigger | Resolution |
|---|---|---|
| **Tile** | Vision Inspector confidence < 0.80 on any defect | Operator must classify or confirm; agent decision is advisory only |
| **Tile** | Defect class flagged "always escalate" in taxonomy (e.g., tombstoning) | Operator must acknowledge; senior notification logged |
| **Board** | Any tile with status `hold` | Operator must confirm hold; board cannot pass automatically |
| **Lot** | Hold rate > 10% | Lot flagged for engineering review |

Operator can **always override** the agent. Overrides are recorded with rationale text and operator ID. Override patterns are tracked across sessions — useful for senior review and for retraining target identification.

## 4. Evidence record contents

Each tile generates one evidence record containing:

- Tile metadata (board_id, position, magnification, timestamp, operator_id).
- Captured image (stored in GCS, referenced by URL).
- Vision Inspector raw output (defects with bboxes, classes, confidences).
- FMEA Risk Agent decision (severity, recommended action, justification text).
- Supervisor Agent final action.
- Operator action (accept / override) with timestamp.
- Operator rationale text (if override).

Each board generates one aggregated `QCReport` containing:

- All tile evidence records (by reference).
- Defect histogram across the board.
- Heatmap data (tile-level severity grid).
- Board-level action and operator sign-off.
- Optional senior notification record (if escalated).

Each lot generates one lot summary:

- Roster of boards in lot.
- Pass / rework / hold counts.
- Lot-level action.

All records are immutable once signed off (append-only audit log).

## 5. Throughput targets for the demo

These are illustrative numbers for the submission demo, not contractual SLAs:

- **Tile latency end-to-end:** ≤ 8 seconds (capture → display agent decision).
- **Operator review time per tile:** ≤ 5 seconds for `pass`, ≤ 15 seconds for `rework`, ≤ 30 seconds for `human_review`.
- **Throughput with 600-tile board:** ≤ 90 minutes per board with one operator. Without the agent, the same inspection by an unaided junior operator typically requires 4–6 hours, and the result is less reliable.
- **Operator-agent agreement target:** ≥ 92% on `pass` and `rework` decisions, measured on a held-out validation set drawn from PKU-Market-PCB.

## 6. What the operator does *not* see

- The four-agent decomposition is invisible to the operator. UI presents one agent ("RoboQC") with one decision per tile.
- The internal confidence numbers are visible only as a color-coded indicator (green / yellow / red), not as raw probabilities. Operators are not Bayesian reasoners.
- Provider-side details (Gemini calls, ADK graph state, ExecutionStore SQL) are hidden. Backend telemetry is available to engineers via Cloud Run monitoring.

## 7. What we are not building for the demo

- No production microscope integration. Tile capture in the demo is **upload an image file**, simulating the microscope capture step. Real microscope SDK integration is a post-submission item.
- No multi-operator collaboration (no Senior QC UI). All HITL routing in the demo is to a single operator role.
- No on-device inference. All agent calls go to Vertex AI Gemini in us-central1. Real product would have an edge inference option; out of scope for submission.
- No SMT process analytics (root cause inference across multiple boards). Each session is independent. Cross-session analytics is post-submission.

---

## Workflow as a single diagram (text)

```
Operator                          Agent                            Storage
--------                          -----                            -------
[start session]
                          ──────► [QCReport created]               GCS + SQL

[for each tile]
  capture image  ────────►  Vision Inspector
                            ─► defects[]
                          ─► FMEA Risk
                            ─► severity, action
                          ─► Supervisor
                            ─► tile decision
                   ◄──── tile result
  review + accept/override
                          ─► Evidence Report
                                                                   [tile record persisted]

[board complete]
                          ─► Evidence Report aggregates
                          ─► Supervisor → board decision
  sign off
                                                                   [QCReport finalized]

[lot complete]
                          ─► lot rollup
                                                                   [lot summary persisted]
```

This is the workflow the demo video walks through end-to-end.
