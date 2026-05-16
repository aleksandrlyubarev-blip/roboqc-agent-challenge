# AI Collaboration Protocol

**Status:** active  
**Applies to:** Claude + Codex work on `roboqc-agent-challenge`  
**Current operating mode:** pre-submission mode until 2026-06-05 inclusive

## Purpose

The founder should not act as a courier between Claude and Codex.

The goal of this protocol is to let both systems make most day-to-day decisions
independently while preserving:

- product clarity
- execution speed
- reviewability
- founder control over the small number of decisions that truly require it

## Phase 1 — pre-submission mode

**Window:** now through 2026-06-05  
**Priority:** speed with clear ownership, not consensus ritual

### Ownership

| Area | Owner |
|---|---|
| `docs/`, narrative, domain language, system prompts, FMEA taxonomy, business case, submission writeups | Claude |
| `src/`, `bench/`, `infra/`, `tests/`, `scripts/`, CI, deploy, code migration, repo hygiene | Codex |
| Product direction, legal risk, scope changes, budget / deadline tradeoffs | Founder |

### Boundary rule for `src/roboqc_agent/schemas.py`

`schemas.py` is a domain contract authored by Claude and implemented against by
Codex.

Codex may make **engineering-only** edits without founder escalation, for
example:

- stricter typing
- import cleanup
- naming consistency
- validation hardening
- serialization fixes

Codex must record such changes in `decision_log.md`.

Codex must escalate through `open_questions.md` before making **semantic**
changes, for example:

- adding or removing a field
- changing an enum meaning
- changing agent boundaries
- changing the workflow contract between agents

### Default decision rule

Before 2026-06-05, Claude and Codex do **not** run a full consensus loop for
every non-trivial choice.

- If the issue is primarily about code, architecture, infra, tests, or deploy:
  **Codex decides.**
- If the issue is primarily about narrative, product framing, domain language,
  prompts, or taxonomy semantics: **Claude decides.**
- If neither owner is clear, or if the decision changes product scope, legal
  exposure, customer promise, deadline, or money: **escalate to the founder in
  one sentence through `open_questions.md`.**

### How to disagree

If one agent disagrees with the other during Phase 1:

1. Check the ownership table.
2. If ownership is clear, the owner decides and records the decision.
3. If ownership is not clear, escalate once.
4. Do not spend deadline time building comparison tables unless the issue is
   already founder-level.

## Phase 2 — post-submission mode

**Starts:** 2026-06-06  
**Priority:** durable architecture and shared reasoning

After the challenge deadline, Claude and Codex may use a fuller protocol for
important decisions:

1. options considered
2. pros / cons
3. recommendation
4. decision criteria
5. why founder input is or is not required

This is the right long-term mode for work that is no longer under submission
time pressure.

## Escalation policy

Escalate to the founder only when at least one of the following is true:

- product target changes
- customer segment changes
- legal / licensing / confidentiality risk appears
- non-negotiables must be reopened
- deadline, budget, or cloud spend tradeoff changes materially
- Claude and Codex cannot determine ownership cleanly

Otherwise, decide locally and record the result.

## Session restart rule

Claude and Codex are separate systems and do not share durable memory between
sessions. Every fresh session must recover current context from the repository,
not from assumed recollection.

Minimum startup read order:

1. `docs/non_negotiables.md`
2. `docs/codex_brief.md`
3. `docs/decision_log.md`
4. `docs/open_questions.md`
5. the task-specific docs or code under active work

If a fresh session cannot understand a prior decision within roughly 60 seconds
from `decision_log.md`, the log entry is too thin and should be expanded.
