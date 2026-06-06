# Demo — RoboQC Agent walkthrough

This walks the architecture from the operator's seat with a concrete board.
It is the script the submission demo video follows end to end.

## Setup

```bash
pip install -e ".[ui]"
streamlit run ui/streamlit_app.py
```

With no `GOOGLE_CLOUD_PROJECT` set, the UI runs on the offline `DemoProvider`
(deterministic, taxonomy-consistent) so the demo always runs. Set
`GOOGLE_CLOUD_PROJECT` to route the same flow through live Vertex AI Gemini.

## Scenario

A high-mix, low-volume shop builds 1–2 units of a board per day. There is no QC
department; a technician and an engineer own quality between other duties. They
run a first-article inspection on board `BRD-DEMO-001`, lot `LOT-2026-001`.

## Step 1 — Session setup

In the sidebar the operator sets board model, lot ID, operator ID, and
microscope magnification. A board-level QC report is started.

## Step 2 — Tile capture loop

For each microscope tile the operator uploads the capture and clicks
**Run RoboQC on tile**. The four agents run in sequence:

1. **Vision Inspector** (Gemini multimodal) returns defect candidates — class,
   bounding box, confidence, and source (`labeled_detector` for the six
   DeepPCB classes, `anomaly_arm` for the four anomaly classes). Below-floor
   detections are dropped and overlapping ones deduplicated.
2. **FMEA Risk** (Gemini text) maps each defect to severity, default action,
   an operator-readable justification, and a senior-escalation flag, using the
   frozen taxonomy in [`fmea_taxonomy.md`](fmea_taxonomy.md).
3. **Supervisor** aggregates the per-defect friction-policy decisions into one
   tile action — `pass`, `rework`, `hold`, or `human_review` — and gates HITL.
4. **Evidence Report** assembles the immutable `TileReport` audit record.

The UI shows one **RoboQC** decision per tile with a color (🟢/🟡/🔴/🟠). The
operator can expand the **Agent breakdown** to see each agent's contribution and
the full evidence JSON.

### Example tiles

| Tile | Vision Inspector | FMEA Risk | Supervisor |
|---|---|---|---|
| (0,0) | clean | — | 🟢 PASS (confidence 1.00) |
| (3,7) | `spur` @ 0.97 | minor / pass | 🟢 PASS |
| (5,2) | `insufficient_solder` @ 0.91 | major / rework | 🟡 REWORK |
| (9,4) | `short_circuit` @ 0.62 | critical / hold | 🟠 HUMAN_REVIEW (low confidence) |
| (12,1) | `tombstoning` @ 0.98 | critical / hold, escalate | 🔴 HOLD + senior escalation |

Tile (9,4) shows the HITL gate: a low-confidence critical-looking defect routes
the whole tile to a human rather than auto-holding. Tile (12,1) shows an
always-escalate class (`tombstoning`) flagged for senior review because it
signals a lot-wide process problem.

## Step 3 — Board rollup

The **Board rollup** tab aggregates tiles into a `QCReport`:

- board status (any hold → HOLD; else any rework → REWORK; else PASS),
- a defect histogram across the board,
- the senior-escalation count,
- a per-tile action table.

For this board the result is **HOLD** (driven by the short circuit and the
tombstoning), with the tombstoning escalated for senior review.

## What the demo proves

- **Agentic, not a single CV call:** four specialized agents with typed
  contracts, a deterministic policy core, and a human-in-the-loop gate.
- **Audit trail by default:** every tile — clean or not — produces an evidence
  record. Documentation is free, not extra work.
- **Honest engineering:** structured output via Pydantic, deterministic
  decisions where determinism is correct, Gemini where perception is needed,
  and an offline path so the demo always runs.

## What this demo is not

No production microscope integration (tile capture = image upload), no
multi-operator collaboration, no on-device inference — all post-submission per
[`operator_workflow.md`](operator_workflow.md) §7.
