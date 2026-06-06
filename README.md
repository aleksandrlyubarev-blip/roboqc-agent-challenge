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

The four agents are wired into a sequential per-tile pipeline
([`src/roboqc_agent/graph.py`](src/roboqc_agent/graph.py)):
`Vision Inspector → FMEA Risk → Supervisor → Evidence Report`. Vision Inspector
and FMEA Risk are ADK `LlmAgent` definitions driven through the Vertex AI Gemini
provider; Supervisor and Evidence Report are deterministic stages.

## Quickstart

```bash
pip install -e ".[ui]"

# Offline demo — deterministic, no Google Cloud credentials required:
streamlit run ui/streamlit_app.py

# Live inference — set the project to route through Vertex AI Gemini:
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_CLOUD_LOCATION=us-central1   # optional, defaults to us-central1
streamlit run ui/streamlit_app.py
```

Upload a microscope tile image, run the brigade, and inspect the per-agent
breakdown and audit-grade evidence record. The board rollup tab aggregates tiles
into a board-level QC report with a defect histogram and senior-escalation count.

Programmatic use:

```python
from roboqc_agent.graph import RoboQCPipeline
from roboqc_agent.providers.demo import DemoProvider

pipeline = RoboQCPipeline(DemoProvider())          # or VertexGeminiProvider(...)
report = pipeline.inspect_tile(tile, "tile.png")   # -> TileReport with Action + evidence
```

## Development

```bash
pip install -e ".[dev]"
ruff check . && black --check . && mypy && pytest
```

## Datasets

Public, commercially-licensed PCB datasets only — see
[`scripts/download_datasets.sh`](scripts/download_datasets.sh) and
[`data/CITATIONS.md`](data/CITATIONS.md).

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
