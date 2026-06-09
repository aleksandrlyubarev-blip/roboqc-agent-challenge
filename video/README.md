# Demo video pipeline (V5)

Reproducible build of the hackathon demo video. No design tools needed —
frames are drawn with PIL, assembly is ffmpeg.

```bash
pip install pillow            # + ffmpeg on PATH (apt install ffmpeg)
python video/make_frames.py   # -> video/frames/v5_01..v5_08.png (2400x1350)
python video/make_video.py    # -> video/out/neuron_vision_V5_fable.mp4
```

Output: 1920×1080, 24 fps, H.264 two-pass at 300 kbps, exactly 175 s,
~6.7 MB (submission limit is 8 MB). Each frame gets a slow Ken Burns
push-in and segments are joined with 0.7 s crossfades.

The voice-over script with timecodes matched to this cut is in
`VO_SCRIPT_V5.md` — record it over the silent track, or feed it to TTS.

`frames/` and `out/` are generated and git-ignored; the two Python files
are the source of truth.
