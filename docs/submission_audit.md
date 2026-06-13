# Submission Audit

Last local audit target: Neuron Vision Arize-track package, before final
YouTube/Vimeo upload and Devpost submission.

## Current Local Evidence

- Live demo URL is documented: https://neuron-vision-display-z3mwyxcila-uc.a.run.app
- Devpost copy is prepared: `docs/devpost_submission.md`
- Video upload metadata is prepared: `docs/video_upload.md`
- Final video candidate exists: `video/neuron_vision_V5_final.mp4` (1920×1080, 175 s, narrated)
- Narrated script with per-claim fact-check table: `video/VO_SCRIPT_V5.md`
- Video is fully reproducible from source: `video/make_frames.py`, `video/make_vo.py`, `video/make_video.py`

## Honesty review (resolved)

- Earlier placeholder Phoenix metrics (142 traces / 98.6% / 6.2 s P95) were
  removed from the video, narration, and all docs. Frame 06 now shows only
  structural facts verifiable from code: 6 spans per inspection,
  schema-validated outputs, no free-text decisions.
- Devpost copy and README lead with the deployed stack (Vertex AI Gemini +
  Arize Phoenix). The Google ADK scaffold under `src/roboqc_agent` is
  explicitly marked legacy and not claimed as the deployed system.
- Product name standardized to **Neuron Vision** everywhere user-facing.
- Narration is synthesized (Edge TTS) and disclosed as such in `video/README.md`.

## Verification Command

```bash
python scripts/verify_submission.py --run-pytest
```

Expected pre-upload result:

- Local checks pass.
- `pytest -q` passes.
- Cloud Run live URL returns HTTP 200 and Streamlit HTML shell.
- One pending item remains: final YouTube/Vimeo URL is still a placeholder.

## Final External Steps

1. Upload `video/neuron_vision_V5_final.mp4` as an unlisted YouTube/Vimeo video.
2. Use title, description, and tags from `docs/video_upload.md`.
3. Patch the final URL:

```bash
python scripts/set_final_video_url.py "https://YOUR_UNLISTED_VIDEO_URL"
```

4. Run strict verification:

```bash
python scripts/verify_submission.py --run-pytest --strict-final
```

5. Submit the Devpost form.
