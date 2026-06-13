"""Synthesize the V5 voice-over with edge-tts and lay each segment on a
175 s timeline at its script cue point, so the narration stays in sync with
the visuals. Produces video/vo_audio.mp3 (mono, ~175 s).

Spoken text below is the blockquote prose from VO_SCRIPT_V5.md only — no
stage directions, timecodes, or headers. Offsets are the segment start
timecodes from that script.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SEG_DIR = HERE / "vo_segments"
TOTAL = 175.0  # match the silent cut

# (start_offset_seconds, spoken_text)
SEGMENTS = [
    (0, "An automated optical inspection machine costs half a million to a "
        "million dollars. That's the entry ticket for catching solder defects "
        "on a PCB line. Most small electronics shops never pay it. They inspect "
        "by eye, and defects ship."),
    (18, "Neuron Vision replaces that machine with five Gemini agents. A photo "
         "of the board hits the Triage agent, which decides what deserves a "
         "closer look. Then three specialists fan out in parallel: solder "
         "joints, component placement, silkscreen markings. A Chief Inspector "
         "reads all three reports and issues the verdict: pass, or reject with "
         "the defect named and located. Every agent returns structured JSON, "
         "enforced by Pydantic v2 response schemas. No parsing. No prompt glue."),
    (49, "This isn't a slide deck. It's deployed on Cloud Run, running Gemini "
         "2.5 Pro in us-central1, right now. Upload a board photo, get a named, "
         "located defect in seconds. The URL is on screen. Judges, you're "
         "welcome to try to break it."),
    (70, "The three specialists don't queue. One asyncio gather call runs them "
         "concurrently. Sequential inspection took fourteen point one seconds. "
         "Parallel takes four point seven. Same model, same prompts, three "
         "times faster, because the bottleneck was the architecture, not the "
         "model."),
    (92, "Do the math. An AOI machine is up to a million dollars of capex and "
         "weeks of reprogramming for every new board design. Neuron Vision is "
         "zero infrastructure, cents per inspection, and a new design means "
         "editing a prompt. This is QC that scales down to a ten-person shop, "
         "not just up to a gigafactory."),
    (115, "And it's not a black box. Every run is traced with Arize Phoenix. "
          "When an agent disagrees with a human inspector, we replay exactly "
          "what it saw, and what it said."),
    (136, "The whole pipeline is this honest. Typed agents, one gather call, "
          "and response schemas generated straight from Pydantic models. No "
          "frameworks fighting frameworks. Vertex AI and about two hundred "
          "lines of orchestration you can actually read."),
    (159, "Neuron Vision. Factory-grade inspection, no factory budget required. "
          "The demo is live, the repo is open, links on screen. Built for the "
          "Google for Startups AI Agents Challenge, traced end to end with Arize "
          "Phoenix."),
]

VOICE = "en-US-GuyNeural"
# Per-segment speech-rate overrides (1-indexed) to keep each cue inside its
# window. Segment 2 is the longest; nudge it faster so it doesn't bleed into
# segment 3's narration.
RATE = {2: "+10%"}


def dur(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main() -> None:
    SEG_DIR.mkdir(parents=True, exist_ok=True)
    seg_paths: list[tuple[int, Path]] = []
    for i, (off, text) in enumerate(SEGMENTS, 1):
        p = SEG_DIR / f"seg_{i:02d}.mp3"
        cmd = ["edge-tts", "--voice", VOICE, "--text", text,
               "--write-media", str(p)]
        if i in RATE:
            cmd += ["--rate", RATE[i]]
        subprocess.run(cmd, check=True)
        d = dur(p)
        window = (SEGMENTS[i][0] - off) if i < len(SEGMENTS) else (TOTAL - off)
        flag = "  <-- OVERRUNS WINDOW" if d > window else ""
        print(f"seg {i}: start={off:>3}s  speech={d:5.1f}s  window={window:>4}s{flag}")
        seg_paths.append((off, p))

    # Lay each segment on the timeline with adelay, mix, pad/trim to TOTAL.
    inputs: list[str] = []
    filt: list[str] = []
    for idx, (off, p) in enumerate(seg_paths):
        inputs += ["-i", str(p)]
        filt.append(f"[{idx}:a]adelay={off * 1000}|{off * 1000}[a{idx}]")
    mix_in = "".join(f"[a{idx}]" for idx in range(len(seg_paths)))
    filt.append(
        f"{mix_in}amix=inputs={len(seg_paths)}:normalize=0,"
        f"apad,atrim=0:{TOTAL},aresample=44100[out]"
    )
    out = HERE / "vo_audio.mp3"
    subprocess.run(
        ["ffmpeg", "-y", *inputs,
         "-filter_complex", ";".join(filt),
         "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "4", str(out)],
        check=True,
    )
    print(f"\nwrote {out} ({dur(out):.1f} s)")


if __name__ == "__main__":
    main()
