# FMEA Defect Taxonomy — SMT First-Article Inspection

**Status:** FROZEN for Google submission. Frozen 2026-05-16.
**Scope:** Defines the 10 defect classes that RoboQC Agent recognizes, with severity, visual signature, and recommended action.

This document is the single source of truth for the `FMEAEntry` Pydantic schema and for the FMEA Risk Agent system prompt.

---

## Severity model

Three-level severity, mapped to RPN-style logic but simplified for agent decision-making:

| Severity | Meaning | Default Supervisor action |
|---|---|---|
| **Critical** | Functional failure certain or near-certain. Board is non-conforming. | `hold` — stop the lot, escalate to senior |
| **Major** | Functional failure likely or reliability risk over time. | `rework` — board can be repaired |
| **Minor** | Cosmetic or marginal; functionally acceptable. | `pass` with annotation |

Supervisor Agent can override default action based on confidence and context — see `operator_workflow.md` for HITL gates.

---

## Defect classes

### Class 1 — Open trace

- **Source:** DeepPCB labeled.
- **Visual signature:** continuous copper trace shows a gap; substrate visible through the break. Often single-pixel-width at low magnification.
- **Severity:** Critical (electrical discontinuity, board is non-functional on that net).
- **Default action:** `hold`.
- **HITL trigger:** confidence < 0.85, or detection in a high-density region with multiple parallel traces.

### Class 2 — Short circuit

- **Source:** DeepPCB labeled.
- **Visual signature:** unintended copper bridge between two adjacent traces or pads. Bridge geometry is irregular (vs. designed bridge which would be straight and uniform).
- **Severity:** Critical.
- **Default action:** `hold`.
- **HITL trigger:** confidence < 0.85, or short involves power/ground net (operator must confirm net identity).

### Class 3 — Mousebite

- **Source:** DeepPCB labeled.
- **Visual signature:** small semicircular notch on the edge of a trace, reducing trace width locally. Resembles a small bite.
- **Severity:** Major (does not break the net immediately but reduces current capacity and reliability).
- **Default action:** `rework` if accessible, otherwise `pass` with annotation.
- **HITL trigger:** if estimated notch depth > 30% of trace width → escalate to senior.

### Class 4 — Spur

- **Source:** DeepPCB labeled.
- **Visual signature:** small protrusion of copper extending from a trace into the surrounding substrate, not connecting to anything. Irregular shape.
- **Severity:** Minor on its own, but elevates to Major if spur length brings it close to a neighboring net (proximity short risk).
- **Default action:** `pass` with annotation; `rework` if proximity to neighbor < 100 µm.
- **HITL trigger:** spur length > 50% of trace width.

### Class 5 — Excess copper

- **Source:** DeepPCB labeled.
- **Visual signature:** copper deposit in an area where the design specifies no copper. Irregular patch shape, often near pad or via.
- **Severity:** Major (reliability risk, potential ESD path, possible short under thermal cycling).
- **Default action:** `rework`.
- **HITL trigger:** copper patch overlaps a designed feature edge.

### Class 6 — Pinhole

- **Source:** DeepPCB labeled.
- **Visual signature:** small circular void inside a copper pad or trace. Substrate visible through the hole.
- **Severity:** Minor unless on a pad (then Major, soldering reliability).
- **Default action:** `pass` for trace, `rework` for pad.
- **HITL trigger:** pinhole on a fine-pitch pad (< 0.5 mm pitch).

### Class 7 — Tombstoning

- **Source:** anomaly-detection arm (Gemini multimodal + VisA-style validation).
- **Visual signature:** a passive component (resistor, capacitor) stands vertically on one end pad, the other end lifted away from its pad. Looks like a tombstone.
- **Severity:** Critical (component is electrically disconnected on one end).
- **Default action:** `hold`.
- **HITL trigger:** always escalate to senior on first-article — tombstoning indicates a process problem affecting the entire lot.

### Class 8 — Solder bridge

- **Source:** anomaly-detection arm.
- **Visual signature:** solder fillet extends from one pad to an adjacent pad, forming an unintended electrical connection. Smooth, shiny, metallic surface.
- **Severity:** Critical.
- **Default action:** `hold`, then `rework` if confirmed isolated incident.
- **HITL trigger:** confidence < 0.80, or bridge spans more than two pads.

### Class 9 — Insufficient solder

- **Source:** anomaly-detection arm.
- **Visual signature:** solder fillet is small, dull, or absent on one side of a component lead. Lead may be visible above the pad rather than wetted into solder.
- **Severity:** Major (intermittent contact risk over thermal cycling and vibration).
- **Default action:** `rework`.
- **HITL trigger:** insufficient solder on a high-pin-count IC (BGA, QFN, QFP > 64 pins).

### Class 10 — Missing component

- **Source:** anomaly-detection arm.
- **Visual signature:** designated pad pair shows solder paste with no component placed on top, or empty pads. Tile differs from reference tile of same board position.
- **Severity:** Critical (functional failure guaranteed).
- **Default action:** `hold`.
- **HITL trigger:** missing component is a 0201/0402 passive (placement machine error likely) → annotate for process review.

---

## Summary table

| # | Defect | Source | Severity | Default action |
|---|---|---|---|---|
| 1 | Open trace | DeepPCB | Critical | hold |
| 2 | Short circuit | DeepPCB | Critical | hold |
| 3 | Mousebite | DeepPCB | Major | rework |
| 4 | Spur | DeepPCB | Minor→Major | pass / rework |
| 5 | Excess copper | DeepPCB | Major | rework |
| 6 | Pinhole | DeepPCB | Minor→Major | pass / rework |
| 7 | Tombstoning | Anomaly | Critical | hold |
| 8 | Solder bridge | Anomaly | Critical | hold |
| 9 | Insufficient solder | Anomaly | Major | rework |
| 10 | Missing component | Anomaly | Critical | hold |

---

## Confidence calibration

Detection confidence from Vision Inspector Agent (Gemini multimodal output) is normalized to [0.0, 1.0]. The FMEA Risk Agent uses confidence-aware action:

- `confidence ≥ 0.95` → execute default action directly.
- `0.80 ≤ confidence < 0.95` → execute default action, but flag the evidence record for senior review.
- `confidence < 0.80` → Supervisor Agent routes to `human_review` (HITL gate). Operator decides.

These thresholds are initial values for the submission. Conformal calibration (from `RomeoFlexVision/claude/roboqc-dataset-preparation-cUBoX` reliability work) will refine these post-MVP.

---

## What this taxonomy is not

- Not a production-grade FMEA. A real-world FMEA would include occurrence and detection ratings, root cause analysis, and corrective action plans. This is the inspection-decision subset suitable for an AI agent operating during inspection.
- Not exhaustive for SMT. Real SMT has 30+ recognized defect types (IPC-A-610). This is the demonstration subset selected for coverage of all three severity levels and both labeled and anomaly-detected sources.

Post-submission expansion follows IPC-A-610 as the canonical reference.
