# RoboQC Agent

**RoboQC Agent** is an ADK-native multimodal co-pilot for first-article SMT
(surface-mount technology) PCB inspection under a microscope. A QC technician
scans a board tile by tile; the agent flags suspect tiles, classifies defects,
maps them to FMEA severity, and recommends the next action — always keeping the
human operator in the loop.

> **Status: R&D prototype / public challenge submission.** The domain design is
> frozen and the core contracts, decision policy, provider, persistence, and
> deployment scaffolds are implemented and tested. The end-to-end runtime graph,
> the operator UI, and the benchmark results are still in progress. This repo is
> built to be **inspected honestly**, not to imply a deployed product.
>
> **Reviewing this repo?** Start with **[`PARTNER_REVIEW.md`](PARTNER_REVIEW.md)**
> for a short, link-first entry point, then see
> **[`PUBLIC_EVIDENCE.md`](PUBLIC_EVIDENCE.md)** for the full map of exactly what
> exists today (and what does not).

## What it is

First-article inspection — the manual check of a small pre-production run — is
the manufacturing stage where automated optical inspection lines are too costly
to justify, so the work falls to scarce senior QC technicians. RoboQC Agent is a
co-pilot that lets a less-experienced operator perform that inspection faster and
with an audit-grade evidence trail. It **assists**; it does not replace the
operator, and every decision is advisory and overridable.

The system is organized as four cooperating ADK agents over a shared, typed
contract:

1. **Vision Inspector** — analyzes a microscope tile, returns defect candidates.
2. **FMEA Risk** — maps each defect to severity and inspection consequence.
3. **Supervisor** — decides `pass`, `rework`, `hold`, or `human_review`.
4. **Evidence Report** — assembles tile / board / lot evidence records.

All inter-agent messages are the Pydantic contracts in
[`src/roboqc_agent/schemas.py`](src/roboqc_agent/schemas.py). The deterministic
core of the routing decision lives in
[`src/roboqc_agent/policy/engine.py`](src/roboqc_agent/policy/engine.py) and does
not depend on a model being correct.

## Quickstart (verify the implemented parts)

Requires Python 3.11. No cloud credentials or GPU are needed to run the tests.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

pytest          # unit tests
ruff check .    # lint
black --check . # format
mypy            # strict types
```

All four pass on a clean checkout. The same gate runs in CI
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Implementation status

| Component | Status |
|---|---|
| Typed inter-agent contracts (`schemas.py`) | Implemented, tested |
| Deterministic inspection policy engine | Implemented, tested |
| Vision Inspector / FMEA Risk ADK factories | Implemented, tested |
| Vertex Gemini provider (structured output) | Implemented, tested |
| Execution store, telemetry, request log, FastAPI | Implemented, tested |
| Cloud Run + monitoring scaffolds | Scaffold (lint/parse-verified) |
| Dataset preparation (public sources only) | Implemented |
| Benchmark harness | Scaffold — **no measured results yet** |
| ADK runtime graph wiring | Scaffold / in progress |
| Streamlit operator UI | Planned |

See [`PUBLIC_EVIDENCE.md`](PUBLIC_EVIDENCE.md) for paths, tests, and the
measured-vs-target policy.

## Datasets & licensing

The evaluation corpus is **public datasets only**, used under their published
terms and tracked in [`data/CITATIONS.md`](data/CITATIONS.md). No dataset
payloads are committed.
[`scripts/download_datasets.sh`](scripts/download_datasets.sh) fetches DeepPCB
and the VisA PCB1–4 subset from official sources; PKU-Market-PCB is intentionally
held until its primary-source license note is recorded. No proprietary imagery,
customer data, or NDA-encumbered material is used.

## Documentation

**Domain source of truth**

- [`docs/inspection_target_spec.md`](docs/inspection_target_spec.md) — use case, datasets, tile model
- [`docs/fmea_taxonomy.md`](docs/fmea_taxonomy.md) — frozen 10-class defect taxonomy
- [`docs/architecture.md`](docs/architecture.md) — four-agent design and data flow
- [`docs/operator_workflow.md`](docs/operator_workflow.md) — human-in-the-loop workflow

**Project process (working agreements)**

- [`docs/decision_log.md`](docs/decision_log.md) — append-only design decisions
- [`docs/non_negotiables.md`](docs/non_negotiables.md) — frozen scope for the submission
- [`docs/ai_collaboration_protocol.md`](docs/ai_collaboration_protocol.md) — how the contributors divide work
- [`docs/open_questions.md`](docs/open_questions.md) — escalation queue

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
