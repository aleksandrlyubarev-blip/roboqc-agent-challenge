# Public Evidence — RoboQC Agent

This page is a curated, link-first map of what is **actually in this repository
today**, so a reviewer can inspect the real artifacts in a few minutes without
taking any claim on faith.

It is deliberately honest about maturity. RoboQC Agent is an **R&D / challenge
submission prototype**, not a deployed product. Where something is a design
document, a scaffold, or a planned extension, this page says so.

For a shorter entry point, see [`PARTNER_REVIEW.md`](PARTNER_REVIEW.md).

---

## Partner review path

Recommended order for a technical partner review:

1. **[`README.md`](README.md)** — orientation, status table, quickstart.
2. **Core code** — [`src/roboqc_agent/schemas.py`](src/roboqc_agent/schemas.py)
   (contracts) → [`src/roboqc_agent/policy/engine.py`](src/roboqc_agent/policy/engine.py)
   (deterministic decision core) → [`src/roboqc_agent/telemetry/`](src/roboqc_agent/telemetry/)
   (observability) → [`tests/`](tests/) (what is actually asserted).
3. **[`bench/README.md`](bench/README.md)** — the measured-vs-target policy and
   why no results table exists yet.
4. **Open risks** — §4 (measured vs. target) and §5 (limitations / not yet
   built) below.

---

## 1. Verify it yourself in ~2 minutes

```bash
# Python 3.11
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

pytest          # unit tests for the implemented modules
ruff check .    # lint
black --check . # format check
mypy            # strict type check
```

All four commands pass on a clean checkout of this branch. The CI workflow that
runs the same gate is [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

> No cloud credentials, dataset download, or GPU is required to run the test
> suite. Tests exercise the implemented logic (schemas, policy engine, agent
> factory construction, execution store, telemetry); they do **not** call
> Vertex AI or any external service.

---

## 2. Evidence index

Status legend: **Implemented** = real, tested code that runs today ·
**Scaffold** = structural placeholder with a defined contract ·
**Planned** = documented intent, not yet built.

| Area | Path | Status | What it demonstrates |
|---|---|---|---|
| Inter-agent contracts | [`src/roboqc_agent/schemas.py`](src/roboqc_agent/schemas.py) | Implemented | Frozen Pydantic v2 contracts: `Defect`, `FMEAEntry`, `Action`, `TileReport`, `QCReport`, `LotSummary`, and the 10-class defect taxonomy. |
| Decision policy engine | [`src/roboqc_agent/policy/engine.py`](src/roboqc_agent/policy/engine.py) | Implemented | Deterministic, confidence-aware checker mapping `(defect_class, severity, confidence)` → action + HITL escalation. Tested in [`tests/test_policy_engine.py`](tests/test_policy_engine.py). |
| Vision Inspector factory | [`src/roboqc_agent/agents/vision_inspector.py`](src/roboqc_agent/agents/vision_inspector.py) | Implemented | ADK-native agent factory with `output_schema = list[Defect]`. |
| FMEA Risk factory | [`src/roboqc_agent/agents/fmea_risk.py`](src/roboqc_agent/agents/fmea_risk.py) | Implemented | ADK-native text-only agent factory with `output_schema = list[FMEAEntry]`. |
| Supervisor / Evidence factories | [`src/roboqc_agent/agents/`](src/roboqc_agent/agents/) | Scaffold | Module boundary defined; full prompt/runtime wiring tracked in open work (see §5). |
| Vertex Gemini provider | [`src/roboqc_agent/providers/vertex_gemini.py`](src/roboqc_agent/providers/vertex_gemini.py) | Implemented | ADC-based Vertex client with `generate_text` / `generate_multimodal` and structured output. Tested with a fake client in [`tests/test_vertex_gemini.py`](tests/test_vertex_gemini.py). |
| Tool contract + runner | [`src/roboqc_agent/tools/base.py`](src/roboqc_agent/tools/base.py), [`src/roboqc_agent/orchestration/tool_runner.py`](src/roboqc_agent/orchestration/tool_runner.py) | Implemented | Generic typed-tool contract and concurrency-safe runner. Tests: [`tests/test_tools_base.py`](tests/test_tools_base.py), [`tests/test_tool_runner.py`](tests/test_tool_runner.py). |
| Evidence persistence | [`src/roboqc_agent/execution_store/`](src/roboqc_agent/execution_store/) | Implemented | SQLite-backed `QCReport` + append-only event store. Tested in [`tests/test_execution_store.py`](tests/test_execution_store.py). |
| Telemetry + request log | [`src/roboqc_agent/telemetry/`](src/roboqc_agent/telemetry/) | Implemented | Normalized per-call LLM telemetry and structured HTTP request logging. Tests: [`tests/test_llm_telemetry.py`](tests/test_llm_telemetry.py), [`tests/test_request_log.py`](tests/test_request_log.py). |
| HTTP service | [`src/roboqc_agent/api.py`](src/roboqc_agent/api.py) | Implemented | FastAPI app with health endpoints. Tested in [`tests/test_api.py`](tests/test_api.py). |
| Cloud Run deploy | [`infra/cloudrun/`](infra/cloudrun/) | Scaffold | Dockerfile, deploy script, declarative `service.yaml`, and notes. Verified to lint/parse; not a live deployment. |
| Monitoring | [`infra/monitoring/`](infra/monitoring/) | Scaffold | Log-based metric + alert-policy templates for LLM latency, LLM errors, HTTP 5xx, with an idempotent setup script. |
| Dataset preparation | [`scripts/download_datasets.sh`](scripts/download_datasets.sh), [`data/CITATIONS.md`](data/CITATIONS.md) | Implemented | Fetches public DeepPCB + VisA PCB1–4 from official sources; PKU-Market-PCB intentionally held pending license confirmation. No dataset payloads are committed. |
| Benchmark harness | [`bench/`](bench/), [`bench/README.md`](bench/README.md) | Scaffold | Smoke-level harness and runbook. **No measured benchmark results are published** — see §4. |
| ADK graph wiring | [`src/roboqc_agent/graph.py`](src/roboqc_agent/graph.py) | Scaffold | Graph entrypoint; full runtime invocation is open work (see §5). |
| Operator UI | [`ui/streamlit_app.py`](ui/streamlit_app.py) | Planned | Single-file Streamlit surface; not yet implemented. |

### Design documentation (source of truth for the domain)

| Document | Purpose |
|---|---|
| [`docs/inspection_target_spec.md`](docs/inspection_target_spec.md) | The use case, datasets, and tile model. |
| [`docs/fmea_taxonomy.md`](docs/fmea_taxonomy.md) | The frozen 10-class defect taxonomy and severity model. |
| [`docs/architecture.md`](docs/architecture.md) | Four-agent decomposition, data flow, storage, deployment. |
| [`docs/operator_workflow.md`](docs/operator_workflow.md) | End-to-end human-in-the-loop workflow and HITL gates. |
| [`docs/decision_log.md`](docs/decision_log.md) | Append-only record of why the design is the way it is. |

---

## 3. What is genuinely working today

- A **frozen, typed domain contract** (`schemas.py`) shared by every agent.
- A **deterministic decision policy** (`policy/engine.py`) that turns a defect
  classification + confidence into a pass / rework / hold / human-review action,
  with explicit always-escalate handling for tombstoning. This is the part of
  the system that does **not** depend on a model being correct.
- **ADK-native agent factories** for Vision Inspector and FMEA Risk that fix
  their output to the Pydantic contract.
- A **Vertex Gemini provider** abstraction with structured-output support,
  tested against a fake client.
- **Evidence persistence, telemetry, request logging, and a FastAPI surface**,
  each with smoke tests.
- **Deployment and monitoring scaffolds** for Cloud Run.
- A **reproducible dataset path** built only from documented public sources.

Everything above is covered by the test suite and the CI gate.

---

## 4. Measured vs. target metrics — read this before quoting a number

**No performance metric in this repository has been measured yet.** Any latency,
throughput, or agreement figure that appears in the design docs is a **design
target**, not an observed result:

- The "≤ 8 s per-tile latency" budget in [`docs/architecture.md`](docs/architecture.md)
  is a target with a per-step allocation, not a measurement.
- The throughput and "operator–agent agreement" figures in
  [`docs/operator_workflow.md`](docs/operator_workflow.md) are explicitly
  labelled illustrative targets, to be measured against a held-out validation
  set once the runtime flow exists.
- [`bench/`](bench/) currently contains a **smoke-level harness only**. It does
  not yet produce a results table. See [`bench/README.md`](bench/README.md) for
  the runbook and the measured-vs-target policy.

If and when real numbers exist, they will be published in `bench/` with the
exact command, dataset, and commit used to produce them.

---

## 5. Honest limitations / not yet built

- **No end-to-end runtime.** The ADK graph entrypoint exists but full per-tile
  invocation (state keys, persistence after each tile, board finalization) is
  not wired. Prompt text and the committed schema contract still need to be
  reconciled before the graph is an executable LLM flow.
- **No operator UI.** `ui/streamlit_app.py` is a placeholder.
- **No benchmark results.** The harness runs a smoke placeholder only.
- **No image object-storage adapter.** `Tile.image_uri` models an external
  reference; the GCS adapter is intended, not implemented.
- **No live cloud deployment.** Cloud Run and monitoring are reviewable
  scaffolds, not a running service.

---

## 6. Compliance posture

- Apache-2.0 licensed ([`LICENSE`](LICENSE)).
- Evaluation corpus is **public datasets only**, tracked with explicit citation
  and license notes in [`data/CITATIONS.md`](data/CITATIONS.md). No proprietary
  imagery, no customer data, no NDA-encumbered material.
- No secrets or credentials are committed; the provider authenticates via
  Application Default Credentials.
