"""Assemble the Neuron Vision V5 demo video from the frames in video/frames/.

Each frame gets a slow Ken Burns push-in (zoompan) and segments are joined
with crossfades. Output: 1920x1080 @ 30 fps, H.264, ~175 s, well under 8 MB.

Usage:
    python video/make_frames.py
    python video/make_video.py [output.mp4]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FRAMES_DIR = HERE / "frames"
FPS = 24
XFADE = 0.7  # seconds of crossfade between segments
ZOOM = 0.045  # total Ken Burns push-in per segment (keeps bitrate low)
VBITRATE = "300k"  # two-pass target; 175 s * 300 kbps ≈ 6.6 MB video

# (frame file, on-screen seconds before crossfade overlap).
# Sum = 179.9 s; minus 7 crossfades of 0.7 s -> 175.0 s final.
SEGMENTS: list[tuple[str, float]] = [
    ("v5_01_cost_stat.png", 19.0),
    ("v5_02_pipeline.png", 31.0),
    ("v5_03_demo.png", 22.4),
    ("v5_04_speed_compare.png", 22.4),
    ("v5_05_impact.png", 23.4),
    ("v5_06_observability.png", 22.4),
    ("v5_07_tech_code.png", 23.4),
    ("v5_08_cta.png", 15.9),
]


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out" / "neuron_vision_V5_fable.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = ["ffmpeg", "-y"]
    for name, _ in SEGMENTS:
        path = FRAMES_DIR / name
        if not path.exists():
            sys.exit(f"missing frame: {path} — run video/make_frames.py first")
        cmd += ["-loop", "1", "-framerate", str(FPS), "-i", str(path)]

    filters: list[str] = []
    for i, (_, dur) in enumerate(SEGMENTS):
        frames = round(dur * FPS)
        zstep = ZOOM / frames
        filters.append(
            f"[{i}:v]zoompan=z='1+{zstep:.6f}*on':d={frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s=1920x1080:fps={FPS},format=yuv420p,settb=AVTB[v{i}]"
        )

    # chain crossfades
    last = "v0"
    offset = 0.0
    for i in range(1, len(SEGMENTS)):
        offset += SEGMENTS[i - 1][1] - XFADE
        nxt = f"x{i}" if i < len(SEGMENTS) - 1 else "vout"
        filters.append(
            f"[{last}][v{i}]xfade=transition=fade:duration={XFADE}"
            f":offset={offset:.3f}[{nxt}]"
        )
        last = nxt

    total = sum(d for _, d in SEGMENTS) - XFADE * (len(SEGMENTS) - 1)
    print(f"target duration: {total:.1f} s")

    common = cmd + [
        "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=44100",
        "-filter_complex", ";".join(filters),
        "-map", "[vout]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-b:v", VBITRATE,
        "-maxrate", "380k", "-bufsize", "760k",
        "-pix_fmt", "yuv420p",
        "-passlogfile", str(out.parent / "ffpass"),
    ]
    subprocess.run(
        common + ["-an", "-pass", "1", "-f", "null", "/dev/null"], check=True
    )
    subprocess.run(
        common + [
            "-map", f"{len(SEGMENTS)}:a",
            "-c:a", "aac", "-b:a", "16k", "-shortest",
            "-movflags", "+faststart",
            "-pass", "2", str(out),
        ],
        check=True,
    )
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
