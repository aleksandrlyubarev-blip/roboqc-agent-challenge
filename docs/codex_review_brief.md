# Codex Review Brief — four-agent pipeline implementation

**For:** Codex (review pass)
**From:** Claude Code
**Date:** 2026-06-06
**Branch:** `claude/project-context-brief-nBVeF`
**Commit:** `eed5ec9` ("feat: implement four-agent inspection pipeline")
**Base:** `main`
**Scope of change:** 21 files, +2009 / −20.

This brief tells you exactly what changed, where it lives, why, and how to
verify it. The full reasoning is in `docs/decision_log.md` (three new entries
dated 2026-06-06). The architectural contract is unchanged — `schemas.py` and
the four-agent decomposition are untouched.

---

## How to verify (one block)

```bash
git fetch origin claude/project-context-brief-nBVeF
git checkout claude/project-context-brief-nBVeF
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && black --check . && mypy && pytest        # all green: 49 passed
pip install -e ".[ui]"
streamlit run ui/streamlit_app.py                        # offline demo, no GCP creds
```

Expected: `ruff` OK, `black` OK, `mypy` (strict) OK, `pytest` 49 passed.

---

## What was built

The repo already had: schemas, Vision Inspector + FMEA Risk factories (stubs of
the rest), provider, policy engine, execution store, telemetry, infra, CI. The
missing pieces were the graph, two agents (Evidence Report, Supervisor), the
prompts, and the UI. All are now implemented on the **frozen 4-agent schema**.

### New files

| File | Purpose |
|---|---|
| `src/roboqc_agent/taxonomy.py` | In-code single source for the 10 frozen defect classes (severity, default action, source, always_escalate). Encoded from `docs/fmea_taxonomy.md`. |
| `src/roboqc_agent/prompts.py` | System prompts for Vision / FMEA / Evidence summary. Injected into the ADK factories at build time. |
| `src/roboqc_agent/providers/demo.py` | `DemoProvider`: deterministic offline stand-in for `VertexGeminiProvider` (UI + CI run with no GCP creds). |
| `tests/test_supervisor.py` | 6 tests for the decision logic. |
| `tests/test_evidence_report.py` | 8 tests for aggregation + persistence. |
| `tests/test_graph.py` | 4 tests for the pipeline (fake provider, JSON-text fallback, clean tile, demo provider). |
| `tests/test_taxonomy.py` | 3 tests: taxonomy ↔ policy consistency. |
| `DEVPOST.md` | Submission text draft + 3-min video script. |

### Modified files

| File | What changed |
|---|---|
| `src/roboqc_agent/agents/supervisor.py` | Was a stub. Now `decide_action(tile_id, defects, fmea_entries)` — deterministic per-tile `Action`. |
| `src/roboqc_agent/agents/evidence_report.py` | Was a stub. Now `assemble_tile_report` / `aggregate_board` / `aggregate_lot` / `summarize_board` + `EvidenceReporter`. |
| `src/roboqc_agent/graph.py` | Was a stub. Now `RoboQCPipeline` + `InspectionProvider` protocol. |
| `src/roboqc_agent/agents/vision_inspector.py` | Added `DefectObservation` + `to_defects` (confidence floor, dedup, tile linkage); output_schema now `list[DefectObservation]`. |
| `src/roboqc_agent/agents/fmea_risk.py` | Added `FMEAObservation` + `to_fmea_entries` (order linkage); output_schema now `list[FMEAObservation]`. |
| `src/roboqc_agent/agents/__init__.py` | Re-exports the new symbols. |
| `ui/streamlit_app.py` | Was a 1-line stub. Full operator UI. |
| `tests/test_vision_inspector.py`, `tests/test_fmea_risk.py` | Updated for the new output_schema + mapper tests. |
| `pyproject.toml` | Added `[project.optional-dependencies] ui = ["streamlit"]`. |
| `README.md`, `docs/demo.md`, `docs/decision_log.md` | Quickstart, walkthrough, 3 decision entries. |

---

## Three decisions to scrutinize (logged in decision_log.md)

1. **Agents emit observation models; code assigns identities.**
   `Defect.tile_id` / `defect_id` and `FMEAEntry.defect_id` are provenance the
   model cannot know, so Vision/FMEA now output `DefectObservation` /
   `FMEAObservation` and `to_defects` / `to_fmea_entries` link them to the frozen
   schemas. `schemas.py` is unchanged. **Check:** is order-based linkage in
   `to_fmea_entries` (zip with `strict=False`) acceptable, or do you want an
   index field echoed by the model?

2. **Supervisor is deterministic, aggregates per-defect policy decisions.**
   `decide_action` runs each (defect, FMEA entry) through `FrictionPolicyEngine`
   (architecture §6) and takes the most-stopping action by precedence
   `human_review > hold > rework > pass`. This makes the low-confidence HITL gate
   **per-defect**, not aggregate-max as in §2.4 — a deliberate, stricter
   refinement (any uncertain defect → human). `Action.confidence` still stores
   the aggregate max. **Check:** confirm you accept the per-defect gate over the
   §2.4 aggregate-max wording.

3. **v1 graph executes via the provider, not the ADK Runner.**
   `RoboQCPipeline` drives the two ADK `LlmAgent` definitions through the
   injected Vertex provider; Supervisor/Evidence are deterministic stages. Full
   ADK `Runner` + `SequentialAgent` execution is deferred (needs live creds +
   session service, can't run in CI). **Check:** agree this is the right v1 seam.

---

## Anti-scope honored (non_negotiables.md)

Exactly four agents; ADK + Vertex Gemini; one Streamlit UI; Cloud Run; public
datasets only; no LangGraph / LiteLLM / ROMA / MCP-in-path; no second frontend.
Compliance scan clean (no forbidden hardware/brand terms).

---

## Open items for the sprint (not done)

- Live Cloud Run deploy run (scaffold exists in `infra/cloudrun/`, not executed).
- Real bbox overlays on the tile image in the UI (currently coordinates in a
  table).
- Anomaly-class recall check on held-out PKU data.
- Board/lot finalize HTTP endpoints on the FastAPI service (`api.py` is health
  only; aggregation functions exist and are tested).

## Round 2 — review fixes applied

All three blocking/medium findings from the Codex review pass are resolved.

1. **High — FMEA length mismatch / false pass (fixed).**
   `supervisor.decide_action` now guards: if any defect has no matching FMEA
   entry (`len(fmea_entries) != len(defects)` or id mismatch), it returns
   `HUMAN_REVIEW` before any action aggregation. A critical defect can no longer
   slip through as PASS. Regression test:
   `tests/test_supervisor.py::test_unmapped_defect_forces_human_review_not_pass`
   (2 defects, 1 FMEA entry → HUMAN_REVIEW).

2. **Medium — Streamlit HITL display-only (fixed).**
   `ui/streamlit_app.py` adds an operator decision form: Accept / Override with a
   required rationale on override, producing an `OperatorResponse` and finalizing
   the `TileReport` (`operator_response` + `finalized_at`). The rollup per-tile
   action table now reflects the operator's effective decision.

3. **Medium — lot approval ignored board signoff (fixed).**
   `aggregate_lot` now returns `IN_PROGRESS` while any board has
   `operator_signoff_at is None`; `APPROVED` / `HOLD_FOR_ENGINEERING` require all
   boards signed off. Regression test:
   `tests/test_evidence_report.py::test_lot_in_progress_until_all_boards_signed_off`.

Order-based FMEA linkage is kept, now gated by the mismatch guard (per the
review's stated condition). Suite: **51 passed**; ruff + black + mypy --strict
clean.

## One open question for the founder (not a code issue)

Naming: the repo calls the **software** "RoboQC Agent" everywhere, while the
original brief reserved "RoboQC" for the robot and "Neuron Vision Display" for
the software. The implementation follows the repo. DEVPOST.md follows the repo
too (RoboQC Agent = software; robot = "RoboQC inspection robot (roadmap)"). If
the founder wants the brief's split, README + DEVPOST need a naming pass.
