# Decision Log

**Mode:** append-only  
**Purpose:** restore decision context for fresh Claude / Codex sessions without
depending on chat history

## Required entry format

Each entry must be detailed enough that a fresh session can recover the decision
in about 60 seconds.

```md
## YYYY-MM-DD — Short decision title

- **Decided by:** Claude | Codex | Founder
- **Area:** product | narrative | code | infra | legal | process
- **Decision:** what changed or was chosen
- **Context:** what problem forced the decision now
- **Alternatives considered:** brief list, even if one line each
- **Why this won:** concrete reasoning, not only the outcome
- **Impact on other agent:** what Claude / Codex must now assume
- **Reversible:** yes | no | expensive
- **Revisit after:** date or condition
```

## Entries

## 2026-05-16 — Submission target fixed on SMT first-article inspection

- **Decided by:** Founder, with Claude framing
- **Area:** product
- **Decision:** RoboQC Agent submission targets SMT first-article inspection
  under microscope, processed tile by tile, with operator-in-the-loop review.
- **Context:** Earlier ideation had drifted across several hardware narratives.
  SMT inspection gave the clearest user, workflow, and measurable value for the
  challenge.
- **Alternatives considered:** broader industrial visual QC; generic PCB anomaly
  detection; less-specific inspection concepts.
- **Why this won:** it has a specific user, specific workflow, measurable
  metrics, natural multimodal inputs, and an honest HITL story.
- **Impact on other agent:** all code, docs, demos, and evaluation should assume
  tile-based SMT inspection as the product center.
- **Reversible:** no before the challenge deadline.
- **Revisit after:** 2026-06-06.

## 2026-05-16 — P0 repository baseline uses SMT-first branch history

- **Decided by:** Codex
- **Area:** process
- **Decision:** New public PR history was rebuilt from a clean SMT bootstrap
  branch instead of publishing earlier local drafts that contained prior
  narrative work.
- **Context:** Public repository history needed to be clean, focused, and free
  of unrelated hardware ideation.
- **Alternatives considered:** continue from the earlier local bootstrap branch;
  force-push a later cleanup; rebuild cleanly from `main`.
- **Why this won:** rebuilding from `main` gave the clearest public history and
  removed unnecessary narrative noise from review.
- **Impact on other agent:** public repository history should now be treated as
  SMT-first from inception.
- **Reversible:** expensive.
- **Revisit after:** not needed unless repo strategy changes.

## 2026-05-16 — `schemas.py` may receive engineering-only Codex edits

- **Decided by:** Claude + Codex agreement
- **Area:** process
- **Decision:** Claude owns schema semantics; Codex may make engineering-only
  schema changes such as stronger typing or validation cleanup and must log them.
- **Context:** Claude authors domain contracts while Codex implements against
  them. Some edits are implementation hygiene rather than product changes.
- **Alternatives considered:** freeze the file entirely; let Codex freely edit
  it; separate semantic and engineering ownership.
- **Why this won:** it preserves domain control without making routine code
  quality improvements wait on founder mediation.
- **Impact on other agent:** semantic changes require escalation; engineering
  changes require documentation, not permission.
- **Reversible:** yes.
- **Revisit after:** 2026-06-06.

## 2026-05-17 — Pre-submission collaboration uses ownership defaults, not consensus loops

- **Decided by:** Claude + Codex agreement
- **Area:** process
- **Decision:** Until 2026-06-05, Claude owns domain / narrative work, Codex
  owns code / infra work, and disagreements follow ownership defaults instead
  of running full comparison-table consensus loops.
- **Context:** The deadline is close enough that full deliberation on every
  non-trivial choice would cost more than it saves.
- **Alternatives considered:** full consensus protocol immediately; founder
  mediation on every disagreement; owner-default protocol until after deadline.
- **Why this won:** it preserves speed while still keeping true founder-level
  decisions visible through `open_questions.md`.
- **Impact on other agent:** ask the owner, not the founder, unless product,
  legal, money, or scope is changing.
- **Reversible:** yes.
- **Revisit after:** 2026-06-06.

## 2026-05-17 — Architecture document follows committed provider and storage contracts

- **Decided by:** Codex
- **Area:** code
- **Decision:** `docs/architecture.md` describes the currently committed
  provider, execution-store, and image-persistence boundaries instead of
  projecting a more advanced future implementation into the v1 baseline.
- **Context:** Claude's first architecture pass correctly captured the product
  shape but went slightly ahead of committed code in three places: provider
  return type, evidence-store breadth, and concrete object-storage status.
- **Alternatives considered:** keep the aspirational wording; immediately expand
  code to match the document; align the document to the current baseline and let
  later implementation widen the surface deliberately.
- **Why this won:** it keeps docs and code truthful while preserving room to add
  tile / lot persistence and a GCS image adapter later without pretending they
  already exist.
- **Impact on other agent:** Claude can rely on the architecture doc as a real
  contract; future narrative docs should not assume unimplemented persistence
  backends, completed image storage, or direct `BaseModel` returns from the
  provider.
- **Reversible:** yes.
- **Revisit after:** when tile-level Evidence Report implementation starts.

## 2026-05-17 — Checkpointing must be ADK-native, not a direct donor transplant

- **Decided by:** Codex
- **Area:** code
- **Decision:** the repo keeps `checkpointing/` as a reserved module, but the
  earlier LangGraph-specific donor implementation is not copied directly into
  the ADK project.
- **Context:** the submission explicitly forbids LangGraph while one donor
  checkpointing module was built around LangGraph semantics.
- **Alternatives considered:** copy the donor unchanged; drop checkpointing
  entirely; keep the module boundary but design it later against the actual ADK
  graph.
- **Why this won:** it preserves the intended reliability concern without
  importing the wrong runtime assumptions.
- **Impact on other agent:** narrative can mention checkpointing as a future
  reliability module, but not as an already-complete LangGraph-derived feature.
- **Reversible:** yes.
- **Revisit after:** when `graph.py` becomes a real ADK workflow.

## 2026-05-17 — Request logging is Cloud Logging-first, not database-backed

- **Decided by:** Codex
- **Area:** code
- **Decision:** the P1 request-log donor is adapted into structured HTTP
  logging for Cloud Run rather than copied as a Postgres writer.
- **Context:** the donor implementation wrote to an Andrew-specific Postgres
  table, while RoboQC has not selected a durable post-submission backend and
  does not need a separate request-log database for the v1 demo.
- **Alternatives considered:** copy the donor unchanged; postpone request
  logging entirely; emit structured request records through the application
  logger and let Cloud Logging capture them.
- **Why this won:** it preserves latency/error visibility now, avoids inventing
  a database commitment the product has not made, and matches the already
  chosen Cloud Run observability path.
- **Impact on other agent:** architecture and deployment docs should describe
  request logging as structured Cloud Logging output, not as a persisted SQL
  subsystem.
- **Reversible:** yes.
- **Revisit after:** once a durable backend is chosen for post-submission
  evidence and analytics.

## 2026-05-18 — Submission auth remains platform-managed in Cloud Run

- **Decided by:** Codex
- **Area:** code
- **Decision:** the v1 deployment scaffold uses Cloud Run IAM and a dedicated
  service account, with no application-level API-key or OAuth middleware added
  to the submission path.
- **Context:** the frozen architecture already specifies Cloud Run IAM, while
  the donor auth module was tailored to an Andrew beta flow with tester API
  keys that RoboQC does not need.
- **Alternatives considered:** transplant donor API-key middleware; add a new
  app-level auth layer; keep auth at the Cloud Run boundary only.
- **Why this won:** it matches the agreed architecture, removes unnecessary
  code and secrets from the demo, and keeps the service posture easy to explain
  to judges.
- **Impact on other agent:** docs and demos should describe one operator-facing
  product with platform-managed service auth, not a beta-key distribution flow.
- **Reversible:** yes.
- **Revisit after:** when the product needs multi-operator external access.

## 2026-05-18 — Monitoring follows emitted telemetry fields, not donor cost assumptions

- **Decided by:** Codex
- **Area:** code
- **Decision:** P1 monitoring ships LLM latency, LLM error, and HTTP 5xx
  artifacts now; a cost alert is deferred until the Vertex provider emits a
  normalized cost field.
- **Context:** the Andrew donor received `cost_usd` from LiteLLM, while the
  current RoboQC provider truthfully emits model, operation, latency, request
  id, and token counts.
- **Alternatives considered:** copy the donor cost alert with a guessed field;
  add an ad hoc pricing estimate now; monitor only fields that the code already
  emits.
- **Why this won:** it keeps observability honest and avoids advertising a
  production signal that the system cannot yet compute reliably.
- **Impact on other agent:** technical docs should describe current monitoring
  as latency/error coverage; cost monitoring remains a later extension.
- **Reversible:** yes.
- **Revisit after:** once normalized per-call cost is part of the provider
  telemetry contract.

## 2026-05-18 — Agent factories accept injected prompts during the submission sprint

- **Decided by:** Claude + Codex ownership protocol
- **Area:** process
- **Decision:** code modules expose ADK agent factories that accept prompt text
  as input; Claude-owned system prompts are not hardcoded prematurely by Codex.
- **Context:** week-1 implementation needs to move while prompt wording remains
  in Claude's domain / narrative ownership lane.
- **Alternatives considered:** block agent code until every prompt lands;
  let Codex author placeholder prompts; separate prompt ownership from agent
  construction.
- **Why this won:** it keeps implementation moving without blurring domain
  ownership or baking disposable prompt text into the first code pass.
- **Impact on other agent:** Claude can ship prompt files later against a stable
  factory boundary; Codex can build and test orchestration around that boundary
  now.
- **Reversible:** yes.
- **Revisit after:** when v0.1 prompt files are committed.

## 2026-06-06 — Agents emit observation models; code assigns identities

- **Decided by:** Claude (code)
- **Area:** code
- **Decision:** Vision Inspector returns `DefectObservation`
  (class/bbox/confidence/source) and FMEA Risk returns `FMEAObservation`
  (severity/default_action/justification/escalate). Code links them to the
  frozen `Defect` / `FMEAEntry` contracts: `to_defects` assigns `tile_id` /
  `defect_id` (plus confidence floor and dedup), `to_fmea_entries` re-attaches
  `defect_id` by input order.
- **Context:** the model cannot know `tile_id` / `defect_id`; making them part
  of the structured-output schema would force the model to invent provenance.
- **Alternatives considered:** keep `list[Defect]` / `list[FMEAEntry]` as the
  model schema and post-fix ids; pass ids into the prompt and have the model
  echo them; introduce observation models mapped in code.
- **Why this won:** identities are provenance the system owns, not content the
  model observes; observation models keep the frozen schemas authoritative and
  the Gemini calls robust.
- **Impact on other agent:** `schemas.py` is unchanged; the inter-agent record
  shapes (`Defect`, `FMEAEntry`) are unchanged. Only the LLM structured-output
  surface changed, with mapping helpers in the agent modules.
- **Reversible:** yes.
- **Revisit after:** if a future ADK Runner path consumes the schemas directly.

## 2026-06-06 — Supervisor is deterministic; aggregates per-defect policy decisions

- **Decided by:** Claude (code)
- **Area:** code
- **Decision:** `supervisor.decide_action` runs each (defect, FMEA entry) pair
  through `FrictionPolicyEngine` (architecture §6) and takes the most-stopping
  action by precedence `human_review > hold > rework > pass`. `Action.reason` is
  generated deterministically (architecture §13.3 recommended default), so the
  Supervisor makes no Gemini call on the per-tile critical path.
- **Context:** §2.4 frames the low-confidence HITL gate on aggregate (max)
  confidence, while §6 makes the policy engine the canonical per-defect HITL
  mechanism. The two needed reconciling in code.
- **Alternatives considered:** aggregate-max gate per §2.4; per-defect policy
  aggregation per §6; an LLM Supervisor for the action itself.
- **Why this won:** per-defect aggregation is the §6 mechanism and is strictly
  safer — any uncertain defect routes the whole tile to a human, the correct
  default for first-article inspection. `Action.confidence` still stores the
  aggregate max per the schema.
- **Impact on other agent:** this is a deliberate refinement of the §2.4 default
  HITL gate (per-defect, not aggregate-max), logged here per doc-hygiene. Demos
  and narrative should describe HITL as "any low-confidence defect → human".
- **Reversible:** yes.
- **Revisit after:** when conformal-calibration HITL (`hitl/`) refines thresholds.

## 2026-06-06 — v1 graph executes the sequential composition via the provider

- **Decided by:** Claude (code)
- **Area:** code
- **Decision:** `graph.RoboQCPipeline` runs the architecture §5.1 sequence
  (Vision → FMEA → Supervisor → Evidence) by driving the two ADK `LlmAgent`
  definitions through the injected Vertex provider, with Supervisor and Evidence
  as deterministic code stages. A `DemoProvider` gives a deterministic,
  taxonomy-consistent offline path so the UI and CI run with no GCP credentials.
- **Context:** the demo must be runnable and the suite testable offline; a full
  ADK `Runner` + `SequentialAgent` execution needs live model credentials and a
  session service that cannot run in CI.
- **Alternatives considered:** full ADK Runner execution now; provider-driven
  sequential pipeline with injectable provider; mock the ADK Runner in tests.
- **Why this won:** it keeps the ADK `LlmAgent` factories as the single source
  of agent configuration, makes the whole flow testable and demoable offline,
  and leaves a clean seam to adopt the ADK Runner post-submission.
- **Impact on other agent:** treat `RoboQCPipeline` as the executable graph; the
  ADK agent factories remain the declarative agent definitions.
- **Reversible:** yes.
- **Revisit after:** when adopting the ADK `Runner` for in-graph execution.
