# RoboQC Agent Challenge

**RoboQC Agent** is an ADK-native multimodal co-pilot for first-article SMT
inspection under a microscope. A QC technician scans a PCB tile by tile; the
agent flags suspect tiles, classifies defects, maps them to FMEA severity, and
recommends the next action while keeping the operator in the loop.

## Submission core

The system is built around four agents:

1. **Vision Inspector** — analyzes microscope tiles and returns defect candidates
2. **FMEA Risk** — maps defects to severity and inspection consequence
3. **Evidence Report** — assembles tile, board, and lot evidence records
4. **Supervisor** — decides `pass`, `rework`, `hold`, or `human_review`

## Source of truth

- [`docs/inspection_target_spec.md`](docs/inspection_target_spec.md)
- [`docs/fmea_taxonomy.md`](docs/fmea_taxonomy.md)
- [`docs/operator_workflow.md`](docs/operator_workflow.md)
- [`src/roboqc_agent/schemas.py`](src/roboqc_agent/schemas.py)
- [`docs/codex_brief.md`](docs/codex_brief.md)

## Working agreements

- [`docs/non_negotiables.md`](docs/non_negotiables.md)
- [`docs/ai_collaboration_protocol.md`](docs/ai_collaboration_protocol.md)
- [`docs/decision_log.md`](docs/decision_log.md)
- [`docs/open_questions.md`](docs/open_questions.md)
