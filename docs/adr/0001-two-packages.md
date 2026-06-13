# ADR 0001: `neuron_vision` is the product runtime, `roboqc_agent` is the ADK reference architecture

**Status:** accepted · 2026-06-10

## Context

The repository ships two sibling packages that both model a multi-agent QC
product:

- `src/neuron_vision` — the deployed Neuron Vision Display path: Streamlit UI
  (`app.py`), 5-agent Gemini brigade (`pipeline.py`), demo mode, the Claude
  Fable 5 reasoning service, and Arize Phoenix tracing. This is what runs on
  Cloud Run today.
- `src/roboqc_agent` — the Google ADK architecture for the SMT first-article
  inspection workflow: frozen Pydantic contracts (`schemas.py`), the four-agent
  graph (`graph.py`), the deterministic friction policy
  (`policy/engine.py` + `orchestration/board_flow.py`), the execution store and
  the FastAPI surface.

The 2026-06-10 audit flagged the duplication (separate Severity/verdict
concepts, separate telemetry, no shared base agent) as the largest
architectural risk.

## Decision

1. `neuron_vision` is the **product runtime**. New user-facing features land
   here.
2. `roboqc_agent` is the **ADK reference architecture** for the regulated
   first-article workflow (evidence records, operator sign-off, policy
   enforcement). It is kept buildable, tested, and deployable
   (`infra/cloudrun/`), but it is not the path behind the public demo.
3. The packages stay separate until a third consumer of the shared concepts
   appears. Extracting a `qc_core` package now would force both packages
   through a contract migration with no immediate payoff; the schemas are
   intentionally different (display-panel visual QC vs. SMT evidence records).
4. What *is* shared must be infrastructural, not domain: if a future change
   needs the same retry/telemetry/caching code in both packages, extract that
   specific module (e.g. `fable5.cache`) instead of merging the domains.

## Consequences

- Contributors should not "fix" the duplication by merging schemas — the
  divergence is intentional and documented here.
- `pyproject.toml` ships both packages in one wheel; the Cloud Run images pick
  the entrypoint (`app.py` for the product, `roboqc_agent.api:app` for the
  reference API), so deployment stays independent.
- Revisit when: (a) a third package needs the shared concepts, (b) the
  roboqc_agent workflow is productized, or (c) the schemas converge naturally.
