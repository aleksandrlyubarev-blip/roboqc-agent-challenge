#!/usr/bin/env python3
"""Verify local Neuron Vision submission materials before Devpost upload."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_DEMO_URL = "https://neuron-vision-display-z3mwyxcila-uc.a.run.app"

EXPECTED_FRAMES = [
    "v5_01_cost_stat.png",
    "v5_02_pipeline.png",
    "v5_03_demo.png",
    "v5_04_speed_compare.png",
    "v5_05_impact.png",
    "v5_06_observability.png",
    "v5_07_tech_code.png",
    "v5_08_cta.png",
]

REQUIRED_FILES = [
    "README.md",
    "docs/demo.md",
    "docs/devpost_submission.md",
    "docs/submission_audit.md",
    "docs/video_upload.md",
    "video/neuron_vision_V5_final.mp4",
    "video/VO_SCRIPT_V5.md",
    "video/README.md",
    "video/make_frames.py",
    "video/make_vo.py",
    "video/make_video.py",
]


class CheckReport:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.pending: list[str] = []

    def pass_(self, message: str) -> None:
        print(f"PASS    {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"FAIL    {message}")

    def pending_(self, message: str) -> None:
        self.pending.append(message)
        print(f"PENDING {message}")


def run_json(cmd: list[str]) -> dict[str, object]:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True, capture_output=True)
    return json.loads(proc.stdout)


def check_required_files(report: CheckReport) -> None:
    for rel in REQUIRED_FILES:
        path = REPO_ROOT / rel
        if path.exists() and path.stat().st_size > 0:
            report.pass_(f"{rel} exists")
        else:
            report.fail(f"{rel} is missing or empty")


def check_frames(report: CheckReport) -> None:
    frame_dir = REPO_ROOT / "video" / "frames"
    if not frame_dir.is_dir():
        report.pending_(
            "video/frames/ not present (git-ignored); run `python video/make_frames.py` to regenerate"
        )
        return

    actual = sorted(path.name for path in frame_dir.glob("v5_*.png"))
    if actual == EXPECTED_FRAMES:
        report.pass_("all 8 expected V5 video frames are present")
    else:
        report.fail(f"video frame set mismatch: expected {EXPECTED_FRAMES}, got {actual}")
        return

    for name in EXPECTED_FRAMES:
        path = frame_dir / name
        with Image.open(path) as img:
            if img.size == (2400, 1350):
                continue
            report.fail(f"{path.relative_to(REPO_ROOT)} is {img.size}, expected 2400x1350")
            return
    report.pass_("all video frames are 2400x1350")


def media_info(path: Path) -> dict[str, object]:
    return run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,width,height,channels,sample_rate",
            "-of",
            "json",
            str(path),
        ]
    )


def check_video(report: CheckReport, rel: str, require_voice: bool) -> None:
    path = REPO_ROOT / rel
    try:
        info = media_info(path)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as exc:
        report.fail(f"{rel} could not be inspected with ffprobe: {exc}")
        return

    duration = float(info.get("format", {}).get("duration", "0"))
    streams = info.get("streams", [])
    if not isinstance(streams, list):
        report.fail(f"{rel} ffprobe stream output is malformed")
        return

    video_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]

    if abs(duration - 175.0) <= 0.25:
        report.pass_(f"{rel} duration is {duration:.3f}s (3-minute limit respected)")
    else:
        report.fail(f"{rel} duration is {duration:.3f}s, expected 175s")

    if video_streams and video_streams[0].get("width") == 1920 and video_streams[0].get("height") == 1080:
        report.pass_(f"{rel} video stream is 1920x1080")
    else:
        report.fail(f"{rel} video stream is not 1920x1080")

    if audio_streams:
        stream = audio_streams[0]
        sample_rate = str(stream.get("sample_rate"))
        channels = int(stream.get("channels", 0))
        if sample_rate in ("44100", "48000") and channels >= 1:
            report.pass_(f"{rel} audio stream is present at {sample_rate} Hz")
        else:
            report.fail(f"{rel} audio stream has sample_rate={sample_rate}, channels={channels}")
    elif require_voice:
        report.fail(f"{rel} has no audio stream")
    else:
        report.pending_(f"{rel} has no audio stream")


def check_docs(report: CheckReport, strict_final: bool) -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    devpost = (REPO_ROOT / "docs" / "devpost_submission.md").read_text(encoding="utf-8")
    demo = (REPO_ROOT / "docs" / "demo.md").read_text(encoding="utf-8")

    for label, text, needles in [
        (
            "README.md",
            readme,
            [
                LIVE_DEMO_URL,
                "video/neuron_vision_V5_final.mp4",
                "video/VO_SCRIPT_V5.md",
                "docs/submission_audit.md",
            ],
        ),
        (
            "docs/demo.md",
            demo,
            ["python video/make_video.py", "neuron_vision_V5_final.mp4"],
        ),
        (
            "docs/devpost_submission.md",
            devpost,
            [LIVE_DEMO_URL, "neuron_vision_V5_final.mp4"],
        ),
    ]:
        missing = [needle for needle in needles if needle not in text]
        if missing:
            report.fail(f"{label} missing expected references: {missing}")
        else:
            report.pass_(f"{label} has expected submission references")

    final_video_match = re.search(r"\*\*Final Video:\*\*\s*(.+)", devpost)
    readme_video_match = re.search(r"\*\*Final video:\*\*\s*(.+)", readme)
    final_video_value = final_video_match.group(1).strip() if final_video_match else ""
    readme_video_value = readme_video_match.group(1).strip() if readme_video_match else ""
    final_url = re.search(r"https?://\S+", final_video_value)
    readme_url = re.search(r"https?://\S+", readme_video_value)

    if final_url and readme_url and final_url.group(0) == readme_url.group(0):
        report.pass_("Final video URL is filled consistently in Devpost copy and README")
    elif final_url and readme_url:
        report.fail("Final video URL differs between Devpost copy and README")
    elif strict_final:
        report.fail("Final video URL is still missing from Devpost copy or README")
    else:
        report.pending_("Final video URL is still a placeholder")


def check_live_url(report: CheckReport, skip_live: bool) -> None:
    if skip_live:
        report.pending_("live URL check skipped")
        return

    request = urllib.request.Request(LIVE_DEMO_URL, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception as exc:
        report.fail(f"live demo URL check failed: {exc}")
        return

    if 200 <= status < 400:
        report.pass_(f"live demo URL responds with HTTP {status}")
    else:
        report.fail(f"live demo URL returned HTTP {status}")
        return

    get_request = urllib.request.Request(LIVE_DEMO_URL, method="GET")
    try:
        with urllib.request.urlopen(get_request, timeout=20) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            content_type = response.headers.get("content-type", "")
    except Exception as exc:
        report.fail(f"live demo GET failed: {exc}")
        return

    required_markers = ["<title>Streamlit</title>", '<div id="root"></div>', "static/js/"]
    missing = [marker for marker in required_markers if marker not in body]
    if "text/html" in content_type and not missing:
        report.pass_("live demo GET returns Streamlit HTML shell")
    else:
        report.fail(
            "live demo GET did not look like the Streamlit app shell "
            f"(content_type={content_type!r}, missing={missing})"
        )


def check_pytest(report: CheckReport, run_pytest: bool) -> None:
    if not run_pytest:
        report.pending_("pytest not run; pass --run-pytest for full local gate")
        return
    try:
        subprocess.run(["pytest", "-q"], cwd=REPO_ROOT, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        report.fail(f"pytest failed: {exc}")
        return
    report.pass_("pytest -q passed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-live", action="store_true", help="Skip Cloud Run live URL check.")
    parser.add_argument("--run-pytest", action="store_true", help="Run pytest -q as part of verification.")
    parser.add_argument(
        "--strict-final",
        action="store_true",
        help="Fail if the final YouTube/Vimeo URL is still missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = CheckReport()

    check_required_files(report)
    check_frames(report)
    check_video(report, "video/neuron_vision_V5_final.mp4", require_voice=True)
    check_docs(report, strict_final=args.strict_final)
    check_live_url(report, skip_live=args.skip_live)
    check_pytest(report, run_pytest=args.run_pytest)

    print()
    if report.failures:
        print(f"FAILED: {len(report.failures)} blocking issue(s)")
        return 1
    if report.pending:
        print(f"LOCAL PASS with {len(report.pending)} pending external/non-run item(s)")
        return 0
    print("PASS: submission package is complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
