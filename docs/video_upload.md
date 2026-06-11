# Video Upload Metadata

Use this when uploading `video/neuron_vision_V5_final.mp4` to YouTube or
Vimeo as an unlisted video.

## Upload Assets

- **Video:** `video/neuron_vision_V5_final.mp4` (1920×1080, 175 s, H.264)
- **Script / timecodes:** `video/VO_SCRIPT_V5.md`
- **Build pipeline:** `video/README.md` (fully reproducible: PIL + Edge TTS + ffmpeg)

## Title

Neuron Vision — Reliable 5-Agent Visual QC for Electronics Manufacturing

## Description

Neuron Vision is a 5-agent visual quality control pipeline for PCB/SMT electronics manufacturing.

Triage Agent identifies high-risk regions. Solder, Component, and Marking inspectors run in parallel. Chief Inspector issues a structured Pydantic-verified verdict. Arize Phoenix/OpenTelemetry traces expose the full waterfall, per-agent latency, and parallel specialist spans.

Built with Vertex AI Gemini 2.5 Pro, Pydantic v2, Streamlit, Cloud Run, and Arize Phoenix.

Live demo: https://neuron-vision-display-z3mwyxcila-uc.a.run.app
GitHub: https://github.com/aleksandrlyubarev-blip/roboqc-agent-challenge

## Tags

Neuron Vision, Arize Phoenix, OpenTelemetry, Vertex AI, Gemini 2.5 Pro, Pydantic, Cloud Run, Streamlit, PCB inspection, SMT manufacturing, visual quality control, AI agents, multi-agent system, Industry 4.0

## Visibility

Set visibility to **Unlisted** for judging.

## After Upload

```bash
python scripts/set_final_video_url.py "https://YOUR_UNLISTED_VIDEO_URL"
python scripts/verify_submission.py --run-pytest --strict-final
```
