# Partner Review — RoboQC Agent

A short, honest entry point for a technical partner reviewing this repository.
Link-first by design: every claim below points at a file you can open.

## 30-second summary

RoboQC Agent is an **ADK-native multimodal co-pilot for first-article SMT PCB
inspection under a microscope**. A QC technician scans a board tile by tile; the
agent flags suspect tiles, classifies defects against a frozen FMEA taxonomy,
and recommends `pass` / `rework` / `hold` / `human_review` — always advisory,
always overridable by the operator.

This is an **R&D / challenge-submission prototype**, not a deployed product. The
domain design is frozen and the core contracts and supporting infrastructure are
implemented and tested; the end-to-end runtime, the operator UI, and benchmark
results are still in progress.

## Implemented and inspectable today

- **Typed inter-agent contracts** — [`src/roboqc_agent/schemas.py`](src/roboqc_agent/schemas.py) (frozen Pydantic v2, 10-class defect taxonomy)
- **Deterministic decision policy** — [`src/roboqc_agent/policy/engine.py`](src/roboqc_agent/policy/engine.py) (confidence-aware routing + HITL escalation; no model dependence)
- **ADK agent factories** — [`vision_inspector.py`](src/roboqc_agent/agents/vision_inspector.py), [`fmea_risk.py`](src/roboqc_agent/agents/fmea_risk.py)
- **Vertex Gemini provider** — [`src/roboqc_agent/providers/vertex_gemini.py`](src/roboqc_agent/providers/vertex_gemini.py) (structured output, tested with a fake client)
- **Evidence store, telemetry, request log, FastAPI** — [`execution_store/`](src/roboqc_agent/execution_store/), [`telemetry/`](src/roboqc_agent/telemetry/), [`api.py`](src/roboqc_agent/api.py)
- **Test suite + CI gate** — [`tests/`](tests/), [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- **Public-only dataset preparation** — [`scripts/download_datasets.sh`](scripts/download_datasets.sh), [`data/CITATIONS.md`](data/CITATIONS.md)

## Scaffold / planned (not finished)

- **Cloud Run + monitoring** — reviewable scaffolds, not a live deployment ([`infra/`](infra/))
- **Benchmark harness** — smoke-level only; **no measured results** ([`bench/README.md`](bench/README.md))
- **ADK runtime graph wiring** — entrypoint exists; full per-tile invocation is open work ([`src/roboqc_agent/graph.py`](src/roboqc_agent/graph.py))
- **Streamlit operator UI** — placeholder ([`ui/streamlit_app.py`](ui/streamlit_app.py))

## Review these first

1. [`README.md`](README.md) — orientation and status table
2. [`src/roboqc_agent/schemas.py`](src/roboqc_agent/schemas.py) — the contracts everything else depends on
3. [`src/roboqc_agent/policy/engine.py`](src/roboqc_agent/policy/engine.py) + [`tests/test_policy_engine.py`](tests/test_policy_engine.py) — the deterministic core
4. [`PUBLIC_EVIDENCE.md`](PUBLIC_EVIDENCE.md) — the full evidence map and the partner review path
5. [`bench/README.md`](bench/README.md) — the measured-vs-target policy

## Verify it yourself

Python 3.11. No cloud credentials or GPU required for the tests.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

pytest          # unit tests
ruff check .    # lint
black --check . # format
mypy            # strict types
```

All four pass on a clean checkout of this branch.

## Known limitations

- No end-to-end runtime, operator UI, or benchmark results yet (see scaffold list above).
- No image object-storage adapter — `Tile.image_uri` models the reference; the GCS adapter is intended, not implemented.
- Performance figures in the design docs are **targets, not measurements** — see [`PUBLIC_EVIDENCE.md`](PUBLIC_EVIDENCE.md) §4.

## Intentionally not public

By design, this repository contains **none** of the following:

- customer data or any operator-supplied imagery;
- proprietary or NDA-encumbered datasets, geometry, or reference boards;
- production deployments, live endpoints, or credentials/secrets.

The evaluation corpus is public datasets only, used under their published terms
([`data/CITATIONS.md`](data/CITATIONS.md)). Provider auth is via Application
Default Credentials; nothing sensitive is committed.
