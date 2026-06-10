# Demo video pipeline (V5)

Reproducible build of the hackathon demo video. No design tools needed —
frames are drawn with PIL, assembly is ffmpeg.

```bash
pip install pillow piper-tts  # + ffmpeg on PATH (apt install ffmpeg)
python video/make_frames.py     # -> video/frames/v5_01..v5_08.png (2400x1350)
python video/make_voiceover.py  # -> video/out/voiceover.wav + captions.srt
python video/make_video.py --audio video/out/voiceover.wav
                                # -> video/out/neuron_vision_V5_fable.mp4
```

Output: 1920×1080, 24 fps, H.264 two-pass at 300 kbps + 48 kbps mono AAC
narration, exactly 175 s, ~7.5 MB (submission limit is 8 MB). Each frame
gets a slow Ken Burns push-in and segments are joined with 0.7 s
crossfades.

The narration is synthesized locally with Piper (`en_US-ryan-high`,
downloaded on first run); every segment is tempo-fitted into its timecode
window, so audio and slides stay in sync by construction. To use a human
recording instead, read `VO_SCRIPT_V5.md` over the same timecodes and pass
that file to `--audio`. `captions.srt` ships alongside for muted playback.

`frames/`, `out/`, and `voices/` are generated and git-ignored; the three
Python files are the source of truth.
