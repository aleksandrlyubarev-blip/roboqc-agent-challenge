# Benchmark harness

This directory holds the evaluation harness for RoboQC Agent.

## Status: scaffold — no measured results are published

The harness is currently a **smoke-level placeholder**. It does **not** yet
produce a results table, and **no benchmark numbers from this repository have
been measured.** Any latency, throughput, recall, or operator-agreement figure
that appears in the design docs (`docs/architecture.md`,
`docs/operator_workflow.md`) is a **design target**, not an observed result.

This is deliberate. A "TBD" table dressed up as results would be misleading, so
there isn't one. When real measurements exist, they will be added here together
with the exact command, dataset snapshot, and commit SHA used to produce them.

## Runbook

### 1. Smoke check (works today, no credentials)

```bash
pip install -e ".[dev]"
python bench/bench_smt_inspection.py --smoke
```

This confirms the harness entrypoint is importable and runnable. It performs no
inference and emits no metrics.

### 2. Prepare the public datasets (required before any real run)

```bash
bash scripts/download_datasets.sh
```

Fetches DeepPCB and the VisA PCB1–4 subset from their official sources into
`data/` (git-ignored). PKU-Market-PCB is intentionally skipped until its
primary-source license note is recorded in `data/CITATIONS.md`. See that file
for sources and terms.

### 3. Full evaluation (not yet implemented)

A real evaluation run will require Vertex AI credentials (Application Default
Credentials) and the prepared datasets, and will exercise the runtime graph once
it is wired. This path is **not implemented yet** — see the limitations in
[`../PUBLIC_EVIDENCE.md`](../PUBLIC_EVIDENCE.md).

## Measured vs. target — reporting policy

When results are published in this directory, each metric must be labelled as
one of:

- **measured** — produced by a reproducible command in this repo, with the
  dataset and commit SHA recorded alongside the number; or
- **target** — a design goal, clearly marked as not-yet-measured.

A metric without a reproducible command behind it is a target, not a result, and
must be labelled accordingly.

## Intended metrics (targets, not yet measured)

| Metric | What it captures | Source target |
|---|---|---|
| Per-tile latency | capture → agent decision | ≤ 8 s budget (`docs/architecture.md`) |
| Operator–agent agreement | share of tiles where operator accepts the recommendation | held-out validation set (`docs/operator_workflow.md`) |
| Defect recall by class | fraction of labelled defects detected | per `docs/fmea_taxonomy.md` classes |
| Evidence completeness | fraction of tiles with a complete audit record | `schemas.py` contract |

These rows define what the harness is being built to measure. None are filled in
yet, by design.
