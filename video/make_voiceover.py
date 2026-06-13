"""Synthesize the V5 voice-over with Piper TTS and build captions.

Produces:
    video/out/voiceover.wav  — full 175 s narration track, segment-aligned
    video/out/captions.srt   — subtitles matched to the narration

Each segment is synthesized separately, then tempo-fitted (atempo <= 1.15)
into its slot in the final cut and placed at segment start + lead-in.

Usage:
    python video/make_voiceover.py
    python video/make_video.py --audio video/out/voiceover.wav
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from make_video import SEGMENTS, XFADE

HERE = Path(__file__).parent
OUT = HERE / "out"
VOICE_DIR = HERE / "voices"
VOICE = "en_US-ryan-high"
VOICE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "en/en_US/ryan/high/en_US-ryan-high.onnx"
)
LEAD_IN = 0.6  # seconds of silence after a segment appears before speech
MAX_TEMPO = 1.15

# Narration per segment — keep in sync with VO_SCRIPT_V5.md.
VO: list[str] = [
    # 01 — hook
    "An automated optical inspection machine costs half a million to a "
    "million dollars. That's the entry ticket for catching solder defects "
    "on a PCB line. Most small electronics shops never pay it. They inspect "
    "by eye, and defects ship.",
    # 02 — architecture
    "Neuron Vision replaces that machine with five Gemini agents. A photo "
    "of the board hits the Triage agent, which decides what deserves a "
    "closer look. Then three specialists fan out in parallel: solder "
    "joints, component placement, silkscreen markings. A Chief Inspector "
    "reads all three reports and issues the verdict: pass, or reject with "
    "the defect named and located. Every agent returns structured JSON, "
    "enforced by Pydantic version two response schemas. No parsing. No "
    "prompt glue.",
    # 03 — live demo
    "This isn't a slide deck. It's deployed on Cloud Run, running Gemini "
    "two point five Pro in U S central one, right now. Upload a board "
    "photo; get a named, located defect in seconds. The URL is on screen. "
    "Judges, you're welcome to try to break it.",
    # 04 — speed
    "The three specialists don't queue. One asyncio gather call runs them "
    "concurrently. Sequential inspection took fourteen point one seconds; "
    "parallel takes four point seven. Same model, same prompts. Three "
    "times faster, because the bottleneck was the architecture, not the "
    "model.",
    # 05 — impact
    "Do the math. An AOI machine is up to a million dollars of capital "
    "expense, and weeks of reprogramming for every new board design. "
    "Neuron Vision is zero infrastructure, cents per inspection, and a new "
    "design means editing a prompt. This is QC that scales down to a "
    "ten-person shop, not just up to a gigafactory.",
    # 06 — observability
    "And it's not a black box. Every run is traced with Arize Phoenix. "
    "When an agent disagrees with a human inspector, we replay exactly "
    "what it saw, and what it said.",
    # 07 — code
    "The whole pipeline is this honest. Typed agents, one gather call, and "
    "response schemas generated straight from Pydantic models. No "
    "frameworks fighting frameworks. Vertex AI, and about two hundred "
    "lines of orchestration you can actually read.",
    # 08 — close
    "Neuron Vision. Factory-grade inspection, no factory budget required. "
    "The demo is live, the repo is open. Built for the Google Cloud Rapid "
    "Agent Hackathon, traced end to end with Arize Phoenix.",
]


def sh(*cmd: str) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())


def ensure_voice() -> Path:
    VOICE_DIR.mkdir(exist_ok=True)
    model = VOICE_DIR / f"{VOICE}.onnx"
    if not model.exists():
        print(f"downloading {VOICE} …")
        sh("curl", "-sL", "-o", str(model), VOICE_URL)
        sh("curl", "-sL", "-o", f"{model}.json", VOICE_URL + ".json")
    return model


def segment_starts() -> list[float]:
    starts, t = [], 0.0
    for _, dur in SEGMENTS:
        starts.append(t)
        t += dur - XFADE
    return starts


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return (
        f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:"
        f"{ms % 60000 // 1000:02d},{ms % 1000:03d}"
    )


def write_srt(cues: list[tuple[float, float, str]], path: Path) -> None:
    lines = []
    for i, (a, b, text) in enumerate(cues, start=1):
        lines += [str(i), f"{srt_time(a)} --> {srt_time(b)}", text, ""]
    path.write_text("\n".join(lines))


def captions_for(text: str, start: float, dur: float) -> list[tuple[float, float, str]]:
    """Split a segment's narration into ~2-line cues, timed by char share."""
    words, chunks, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 84:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        chunks.append(cur)
    total = sum(len(c) for c in chunks)
    cues, t = [], start
    for c in chunks:
        d = dur * len(c) / total
        cues.append((t, t + d - 0.05, c))
        t += d
    return cues


def main() -> None:
    OUT.mkdir(exist_ok=True)
    model = ensure_voice()
    starts = segment_starts()
    total = starts[-1] + SEGMENTS[-1][1]

    cues: list[tuple[float, float, str]] = []
    fitted: list[Path] = []
    for i, text in enumerate(VO):
        raw = OUT / f"vo_{i + 1:02d}_raw.wav"
        fit = OUT / f"vo_{i + 1:02d}.wav"
        subprocess.run(
            ["piper", "-m", str(model), "-f", str(raw)],
            input=text,
            text=True,
            check=True,
            capture_output=True,
        )
        window = SEGMENTS[i][1] - XFADE - LEAD_IN - 0.3
        d = duration(raw)
        tempo = max(1.0, d / window)
        if tempo > MAX_TEMPO:
            sys.exit(
                f"segment {i + 1}: narration {d:.1f}s won't fit {window:.1f}s "
                f"even at {MAX_TEMPO}x — trim the text"
            )
        sh(
            "ffmpeg",
            "-y",
            "-i",
            str(raw),
            "-af",
            f"atempo={tempo:.4f},loudnorm=I=-17:TP=-1.5:LRA=9",
            "-ar",
            "44100",
            "-ac",
            "1",
            str(fit),
        )
        fitted.append(fit)
        spoken = duration(fit)
        print(
            f"segment {i + 1}: {d:5.1f}s -> {spoken:5.1f}s "
            f"(window {window:.1f}s, tempo x{tempo:.2f})"
        )
        cues += captions_for(text, starts[i] + LEAD_IN, spoken)

    # mix all segments onto one silent 175 s canvas
    cmd: list[str] = ["ffmpeg", "-y"]
    for f in fitted:
        cmd += ["-i", str(f)]
    delays = "".join(
        f"[{i}:a]adelay={int((starts[i] + LEAD_IN) * 1000)}:all=1[a{i}];"
        for i in range(len(fitted))
    )
    amix = "".join(f"[a{i}]" for i in range(len(fitted)))
    cmd += [
        "-filter_complex",
        f"{delays}{amix}amix=inputs={len(fitted)}:normalize=0," f"apad,atrim=0:{total:.3f}[out]",
        "-map",
        "[out]",
        str(OUT / "voiceover.wav"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    write_srt(cues, OUT / "captions.srt")
    print(f"wrote {OUT / 'voiceover.wav'} ({duration(OUT / 'voiceover.wav'):.1f}s)")
    print(f"wrote {OUT / 'captions.srt'} ({len(cues)} cues)")


if __name__ == "__main__":
    main()
