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
