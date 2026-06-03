# Codex Migration Brief — RoboQC Agent Challenge

**Status:** FROZEN. Replaces all prior architectural notes. Last update: 2026-05-16.
**Repo target:** `aleksandrlyubarev-blip/roboqc-agent-challenge` (public, Apache 2.0).
**Submission deadline:** 2026-06-05.
**Inspection target:** SMT first-article PCB inspection under microscope (see `inspection_target_spec.md`).

---

## 1. Product truth

- Inspection target is SMT first-article PCB inspection under microscope.
- Pydantic schemas are finalized in `src/roboqc_agent/schemas.py`.
- Existing repositories are selective infrastructure donors only; the product
  core is new and domain-specific.

## 2. Repo structure (final)

```
roboqc-agent-challenge/
├── README.md
├── LICENSE                                # Apache 2.0
├── pyproject.toml
├── .github/workflows/
│   ├── ci.yml
│   └── bench.yml
├── src/roboqc_agent/
│   ├── __init__.py
│   ├── schemas.py                         # delivered, do not modify without alignment
│   ├── agents/
│   │   ├── vision_inspector.py            # NEW — Gemini multimodal
│   │   ├── fmea_risk.py                   # NEW — text-only, consumes Defect → FMEAEntry
│   │   ├── evidence_report.py             # NEW — TileReport / QCReport assembly
│   │   └── supervisor.py                  # NEW — emits Action with HITL gating
│   ├── graph.py                           # ADK graph wiring
│   ├── tools/                             # ← internal-donor core/tools/base.py (generic typed-tool only)
│   ├── orchestration/                     # ← internal-donor core/orchestration/tool_runner.py
│   ├── execution_store/                   # ← reusable execution-store donor
│   ├── policy/                            # ← reusable friction-policy donor
│   ├── hitl/                              # ← reusable conformal HITL donor
│   ├── telemetry/                         # ← internal-donor deploy llm_telemetry + request_log
│   ├── auth/                              # ← internal-donor deploy auth (simplified)
│   ├── checkpointing/                     # ← internal-donor deploy checkpointing
│   └── providers/
│       └── vertex_gemini.py               # NEW — Vertex AI Gemini 2.5 Pro client
├── bench/
│   ├── bench_smt_inspection.py            # submission benchmark harness
│   ├── report.py                          # benchmark report utilities
│   ├── scenarios/                         # tile-level evaluation scenarios
│   └── templates/                         # report HTML templates
├── ui/
│   └── streamlit_app.py                   # NEW — tile capture + review UI
├── infra/
│   ├── cloudrun/                          # ← internal-donor deploy Cloud Run artifacts
│   └── monitoring/                        # ← internal-donor deploy monitoring artifacts
├── data/
│   ├── deeppcb/                           # download script provided, not committed
│   ├── pku/                               # download script provided, not committed
│   └── visa_pcb/                          # download script provided, not committed
├── scripts/
│   └── download_datasets.sh               # NEW — fetches DeepPCB + PKU + VisA PCB subset
├── docs/
│   ├── architecture.md                    # NEW — to write end of week 1
│   ├── inspection_target_spec.md          # delivered
│   ├── fmea_taxonomy.md                   # delivered
│   ├── operator_workflow.md               # delivered
│   └── demo.md                            # NEW — to write end of week 2
└── tests/
    ├── test_schemas.py
    ├── test_vision_inspector.py
    ├── test_fmea_risk.py
    ├── test_evidence_report.py
    ├── test_supervisor.py
    └── test_e2e_smoke.py
```

## 3. Migration priorities (unchanged from prior brief)

**P0 (week 1, day 1–3):**

1. `internal-donor/core/tools/base.py` → `src/roboqc_agent/tools/base.py`. Strip SQL/Pandera/dataframe code. Keep only generic typed-tool contract.
2. `internal-donor/core/orchestration/tool_runner.py` → `src/roboqc_agent/orchestration/tool_runner.py`. Adapt to ADK invocation pattern.
3. execution-store donor + `SQLiteExecutionRepository` → `src/roboqc_agent/execution_store/`. Schema is `TileReport` / `QCReport` from `schemas.py`, not analytical execution.
4. New file `src/roboqc_agent/providers/vertex_gemini.py`: Vertex client via ADC, methods `generate_text()`, `generate_multimodal(images, prompt, response_schema)`.

**P1 (week 1, day 4–7):**

5. `internal-donor` deploy branch → `bridge/llm_telemetry.py`, `request_log.py`, `auth.py`, `checkpointing.py` → `src/roboqc_agent/{telemetry,auth,checkpointing}/`. Simplify auth to Cloud Run IAM + service account.
6. Cloud Run artifacts → `infra/cloudrun/`. Target region `us-central1`.
7. friction-policy donor → `src/roboqc_agent/policy/`. Adapt: input is `(defect_class, severity, confidence)`, output is `ActionKind`.

**P2 (week 2):**

8. conformal HITL donor → `src/roboqc_agent/hitl/`.
9. benchmark donor → `bench/bench_smt_inspection.py` + `report.py` + workflow. Retarget scenarios to defect classes from `fmea_taxonomy.md`.

## 4. Datasets

`scripts/download_datasets.sh` should:
- Download DeepPCB from the official repository (Tang et al., 2019). Verify checksum.
- Download PKU-Market-PCB only after primary-source license note is recorded.
- Download VisA, extract only PCB1, PCB2, PCB3, PCB4 subdirectories.
- Land everything under `data/`, which is in `.gitignore`.

Citations file `data/CITATIONS.md` lists all dataset sources and licenses.
Required before publishing any benchmark or demo artifact.

## 5. Do NOT migrate

- Any SQL validation, AST safety, Pandera, dataframe code from the internal donor codebase.
- the internal donor monolith.
- MCP server (stretch goal only, not in v1 submission).
- Skills architecture from `claude/ai-first-skills-architecture-9sS0J`.
- Any media pipelines (SceneOps, music, video).
- Any code from unrelated internal projects.
- Any domain material unrelated to SMT first-article inspection.

## 6. Conventions

- Python 3.11.
- ADK latest (verify version at start of week 1).
- Vertex AI SDK latest.
- Pydantic 2.x (already used in `schemas.py`).
- All agents are ADK `Agent` or `LlmAgent`. No LangGraph, no LiteLLM, no ROMA.
- Structured output via Pydantic `response_schema` parameter on Gemini calls.
- Pre-commit: ruff + black + mypy strict on `src/roboqc_agent/`.
- Tests for every migrated module: at least one smoke test on day of migration.

## 7. End-of-week-1 deliverables (from Codex to founder)

- Working ADK Vision Inspector running on one DeepPCB image (smoke test).
- Migrated `tools/base.py`, `tool_runner.py`, `execution_store/` with passing tests.
- Vertex provider tested on a multimodal call (image + prompt → structured output).
- Cloud Run deploy script verified on a dummy endpoint.
- One PR per P0 module; one PR per P1 module. No giant merges.

## 8. Compliance reminder

Inspection target is exclusively SMT PCB defect inspection using documented
public datasets and explicit license notes. Any commit, comment, or doc that
drifts outside that scope must be rejected at PR review.
