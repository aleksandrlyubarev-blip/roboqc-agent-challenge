# Demo Run-of-Show

The canonical 3-minute submission video is built by the reproducible **V5
pipeline** in `video/` — see `video/README.md` for build commands and
`video/VO_SCRIPT_V5.md` for the narrated script with per-segment timecodes
and a fact-check table sourcing every claim to a file in this repo.

```bash
pip install pillow edge-tts   # + ffmpeg on PATH
python video/make_frames.py   # 8 frames, 2400x1350, drawn with PIL
python video/make_vo.py       # narration synthesized per segment (Edge TTS)
python video/make_video.py --audio video/vo_audio.mp3
```

Output: `video/out/neuron_vision_V5_fable.mp4` — 1920×1080, 175 s, H.264
two-pass. The shipped candidate is `video/neuron_vision_V5_final.mp4`.

## Timeline (V5)

| Time | Frame | Message |
|---|---|---|
| 0:00–0:19 | Cost stat | AOI machines cost $0.5–1M; small shops inspect by eye |
| 0:19–0:49 | Pipeline | 5 Gemini agents: Triage → [Solder, Component, Marking] → Chief |
| 0:49–1:10 | Live demo | Deployed on Cloud Run — judges invited to try the URL |
| 1:10–1:32 | Speed | Sequential 14.1 s → parallel 4.7 s (one `asyncio.gather`) |
| 1:32–1:55 | ROI | Zero infra, cents per inspection, new design = prompt edit |
| 1:55–2:16 | Observability | Arize Phoenix tracing: 6 spans/inspection, schema-validated outputs, replayable verdicts |
| 2:16–2:39 | Code | Vertex AI + ~200-line orchestrator, Pydantic response schemas |
| 2:39–2:55 | Close | Neuron Vision — live demo + open repo, links on screen |

## Video Title

Neuron Vision — Reliable 5-Agent Visual QC for Electronics Manufacturing

## Honesty notes

- Visuals are stylized slides drawn with PIL — not screen recordings — and
  the narration says so explicitly while pointing judges at the live app.
- Narration is synthesized locally with Edge TTS (`en-US-GuyNeural`), as
  documented in `video/README.md`.
- Every number on screen or in narration is either measured in this repo or
  a structural property of the code (see the fact-check table in
  `video/VO_SCRIPT_V5.md`).

## Final URL workflow

After the final YouTube/Vimeo URL is added to `docs/devpost_submission.md`:

```bash
python scripts/set_final_video_url.py "https://YOUR_UNLISTED_VIDEO_URL"
python scripts/verify_submission.py --run-pytest --strict-final
```
