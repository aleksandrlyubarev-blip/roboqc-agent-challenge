# Prompt / schema handoff

**Date:** 2026-05-19  
**GitHub issue:** https://github.com/aleksandrlyubarev-blip/roboqc-agent-challenge/issues/21  
**Status:** RESOLVED 2026-06-09 — Claude revised all four prompt Output Format
sections to match the frozen schemas (option 1 below). Vision Inspector was
aligned first (commit `4248a4b`); FMEA Risk, Supervisor, and Evidence Report
followed. No schema semantics were changed. See `decision_log.md`
(2026-06-09 entry).

Claude-owned prompt files were copied from `~/Desktop/roboqc_prompts/` without
editing prompt strings. Before committing, Codex checked the Output Format
sections against `src/roboqc_agent/schemas.py` and found that the prompt output
objects do not match the currently committed Pydantic contracts.

## Current mismatch summary

- Vision prompt expects `InspectionObservation`; schema currently has `Defect`.
- FMEA prompt expects `FMEARiskAssessment`; schema currently has `FMEAEntry`.
- Supervisor prompt expects `SupervisorDecision`; schema currently has `Action`.
- Evidence prompt expects `InspectionReport`; schema currently has
  `QCReport` / `TileReport` / `LotSummary`.

The prompts are committed unchanged so Claude can revise them from the exact
source text. The graph remains a skeleton until issue #21 is resolved.

## Codex constraint

Codex should not silently mutate schema semantics or prompt strings to paper
over this mismatch. Either:

1. Claude revises prompt Output Format sections to match current schemas, or
2. Claude proposes explicit schema v1.1 changes via `decision_log.md` /
   `open_questions.md`.
