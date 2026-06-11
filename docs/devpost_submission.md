# Devpost Submission Copy

## Project Title

Neuron Vision — 5-Agent Parallel Visual QC Pipeline with Full Observability

## Short Description

5-agent production-grade visual quality control system for PCB/SMT manufacturing. Triage Agent identifies risk zones, three specialized inspectors run in parallel, and Chief Inspector delivers a structured Pydantic-verified verdict: PASS, REWORK, HOLD, or HUMAN REVIEW. Full OpenTelemetry tracing with Arize Phoenix. Built with Vertex AI Gemini 2.5 Pro, Pydantic v2, Streamlit, and Cloud Run.

## Long Description

Neuron Vision is a multi-agent system designed for real electronics manufacturing quality control.

### Architecture

- **Triage Agent** analyzes the PCB image and identifies high-risk zones such as BGA packages, fine-pitch ICs, and connectors.
- **Parallel Inspection Stage** runs three specialized agents concurrently:
  - Solder Inspector: bridges, cold joints, insufficient solder, excess solder
  - Component Inspector: missing parts, misalignment, orientation, shifted components
  - Marking Inspector: silkscreen, QR codes, polarity marks, traceability labels
- **Chief Inspector** synthesizes structured reports from all inspectors and issues a final verdict using only validated Pydantic v2 models.

### Key Technical Strengths

- True parallel specialist execution with measurable latency improvement over sequential inspection.
- Strict structured outputs via Pydantic v2. Chief Inspector never makes a decision from raw free-form text.
- Full production observability with Arize Phoenix/OpenTelemetry, including parent inspection spans and per-agent waterfall spans.
- Deployed on Google Cloud Run and powered by Vertex AI Gemini 2.5 Pro.
- Demo mode included for reliable judging without requiring live GCP credentials.

The project addresses a real manufacturing pain point: PCB defects are expensive, AOI machines are costly, and manual inspection is inconsistent. Neuron Vision demonstrates how specialized multi-agent systems with strong observability can deliver reliable, auditable decisions in physical-world applications.

## Technologies

Vertex AI Gemini 2.5 Pro, Arize Phoenix, OpenTelemetry, OpenInference, Pydantic v2, asyncio, Streamlit, Cloud Run, Python 3.11.

## Links

- **Live Demo:** https://neuron-vision-display-z3mwyxcila-uc.a.run.app
- **GitHub:** https://github.com/aleksandrlyubarev-blip/roboqc-agent-challenge
- **Final Video Candidate (V5):** `video/neuron_vision_V5_final.mp4` (script: `video/VO_SCRIPT_V5.md`, pipeline: `video/README.md`)
- **Final Video:** https://youtu.be/WETa9dAxfUM?si=4hW-69w6i48cOK-S

## Suggested Devpost Highlights

- Arize Phoenix is not decorative: it exposes the actual agent waterfall and makes parallel execution auditable.
- Pydantic schemas are the decision boundary: validated data moves between agents, not untyped text.
- The deployed UI has a demo mode, so judges can inspect the workflow even if cloud inference limits or credentials are unavailable.
- The system is framed as a foundation for production visual QC in Industry 4.0, not just a chatbot over images.

## Submission Checklist

- [x] Live Cloud Run demo URL added.
- [x] GitHub README includes architecture and submission links.
- [x] V5 demo video built from the reproducible pipeline in `video/` (175 s, 1080p).
- [x] Voice-over script fact-checked against the repo (`video/VO_SCRIPT_V5.md`).
- [x] All on-screen and spoken metrics verifiable from code or measured runs.
- [x] Devpost copy prepared in this file.
- [x] Local verifier available: `python scripts/verify_submission.py --run-pytest`.
- [x] URL patch helper available: `python scripts/set_final_video_url.py "https://YOUR_UNLISTED_VIDEO_URL"`.
- [x] Submission audit prepared: `docs/submission_audit.md`.
- [ ] Final edited video uploaded to YouTube or Vimeo as unlisted.
- [ ] Video URL added above and to Devpost.
- [ ] Final Devpost form submitted.
