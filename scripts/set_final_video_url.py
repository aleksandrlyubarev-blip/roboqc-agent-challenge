#!/usr/bin/env python3
"""Patch the final uploaded video URL into README and Devpost copy."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
DEVPOST_PATH = REPO_ROOT / "docs" / "devpost_submission.md"

README_LABEL = "- **Final video:**"
DEVPOST_LABEL = "- **Final Video:**"


def validate_url(url: str) -> str:
    value = url.strip()
    if not re.fullmatch(r"https?://\S+", value):
        raise argparse.ArgumentTypeError("URL must start with http:// or https:// and contain no spaces")
    return value


def replace_labeled_line(text: str, label: str, replacement: str, insert_after: str) -> str:
    pattern = re.compile(rf"^{re.escape(label)}.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)

    marker = f"{insert_after}\n"
    if marker not in text:
        raise ValueError(f"Could not find insertion marker: {insert_after}")
    return text.replace(marker, f"{marker}{replacement}\n", 1)


def patch_file(path: Path, label: str, url: str, insert_after: str, dry_run: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    replacement = f"{label} {url}"
    updated = replace_labeled_line(original, label, replacement, insert_after)
    changed = updated != original
    if changed and not dry_run:
        path.write_text(updated, encoding="utf-8")
    status = "would update" if dry_run and changed else "updated" if changed else "already current"
    print(f"{status}: {path.relative_to(REPO_ROOT)}")
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", type=validate_url, help="Final unlisted YouTube/Vimeo video URL.")
    parser.add_argument("--dry-run", action="store_true", help="Print intended changes without writing files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    patch_file(
        README_PATH,
        README_LABEL,
        args.url,
        "- **Live demo:** https://neuron-vision-display-z3mwyxcila-uc.a.run.app",
        args.dry_run,
    )
    patch_file(
        DEVPOST_PATH,
        DEVPOST_LABEL,
        args.url,
        "- **Silent Draft Video:** `assets/video/roboqc_demo_draft_3min.mp4`",
        args.dry_run,
    )
    if not args.dry_run:
        print("Next: python scripts/verify_submission.py --run-pytest --strict-final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
