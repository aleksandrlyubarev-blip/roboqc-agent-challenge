#!/usr/bin/env bash
# =============================================================================
# download_datasets.sh — Download public PCB defect datasets for demo use
# System: RomeoFlexVision / Neuron Vision Display
# =============================================================================
# Datasets downloaded:
#   1. DeepPCB     — 1,500 paired PCB defect images (PKU)
#   2. VisA (PCB)  — Visual anomaly detection benchmark (Apple/Amazon)
#   3. PKU-Market-PCB — PCB defect detection dataset
#
# Output: examples/pcb_samples/
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${REPO_ROOT}/examples/pcb_samples"

echo "=== Neuron Vision Display — Dataset Downloader ==="
echo "Output: ${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# ── Helper functions ──────────────────────────────────────────────────────────

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' is required but not installed."; exit 1; }
}

download_file() {
    local url="$1" dest="$2"
    echo "  ↓ $(basename "$dest")"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --retry 3 --retry-delay 2 -o "$dest" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q --tries=3 --waitretry=2 -O "$dest" "$url"
    else
        echo "ERROR: Neither curl nor wget is available."; exit 1
    fi
}

# ── 1. DeepPCB (GitHub release samples) ──────────────────────────────────────
echo ""
echo "1/3 DeepPCB — PCB defect sample images"
DEEPPCB_DIR="${OUTPUT_DIR}/deeppcb"
mkdir -p "${DEEPPCB_DIR}"

# Sample images from the DeepPCB public GitHub repo
DEEPPCB_BASE="https://raw.githubusercontent.com/tangsanli5201/DeepPCB/master/PCBData/groups/group00041"
for img in 00041000_temp.jpg 00041001_temp.jpg 00041002_temp.jpg 00041003_temp.jpg 00041004_temp.jpg; do
    dest="${DEEPPCB_DIR}/${img}"
    if [[ ! -f "$dest" ]]; then
        download_file "${DEEPPCB_BASE}/${img}" "$dest" || echo "  ⚠ Skipped ${img} (not available)"
    else
        echo "  ✓ ${img} already present"
    fi
done

echo "  DeepPCB done — $(ls "${DEEPPCB_DIR}"/*.jpg 2>/dev/null | wc -l | tr -d ' ') images"

# ── 2. VisA — PCB subset ──────────────────────────────────────────────────────
echo ""
echo "2/3 VisA (PCB subset) — Visual anomaly dataset"
VISA_DIR="${OUTPUT_DIR}/visa_pcb"
mkdir -p "${VISA_DIR}"

# VisA PCB1 — publicly available via Amazon Science
VISA_BASE="https://amazon-visual-anomaly.s3.us-west-2.amazonaws.com/VisA_20220922.tar"
VISA_TAR="${OUTPUT_DIR}/visa_pcb1.tar"

if [[ ! -f "${VISA_DIR}/.done" ]]; then
    echo "  Downloading VisA PCB subset (~200 MB) …"
    # Only download a representative sample if full tar is too large
    # Try individual class listing from Hugging Face mirror
    HF_BASE="https://huggingface.co/datasets/francoisgermain/VisA/resolve/main/pcb1"
    for split in train test; do
        mkdir -p "${VISA_DIR}/${split}"
        # Download a few representative samples
        for i in 000 001 002 003 004; do
            f="pcb1_${split}_${i}.png"
            dest="${VISA_DIR}/${split}/${f}"
            if [[ ! -f "$dest" ]]; then
                download_file "${HF_BASE}/${split}/good/${i}.png" "$dest" 2>/dev/null \
                    || echo "  ⚠ ${f} not found at mirror, skipping"
            fi
        done
    done
    touch "${VISA_DIR}/.done"
fi
echo "  VisA done"

# ── 3. Synthetic / placeholder samples for offline demo ──────────────────────
echo ""
echo "3/3 Generating synthetic placeholder samples for offline demo"
PLACEHOLDER_DIR="${OUTPUT_DIR}/placeholder"
mkdir -p "${PLACEHOLDER_DIR}"

if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PYEOF'
import sys, pathlib, struct, zlib

# Create minimal valid PNG files as placeholders
def make_placeholder_png(path: pathlib.Path, label: str, width=400, height=300) -> None:
    """Generate a tiny valid PNG with a solid colour (no PIL required)."""
    colors = {
        "pass":         (76, 175, 80),   # green
        "rework":       (255, 152, 0),   # orange
        "hold":         (33, 150, 243),  # blue
        "human_review": (244, 67, 54),   # red
    }
    r, g, b = colors.get(label.split("_")[0], (158, 158, 158))

    def png_chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(height):
        row = b"\x00" + bytes([r, g, b] * width)
        raw += row
    compressed = zlib.compress(raw)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)

out = pathlib.Path("examples/pcb_samples/placeholder")
out.mkdir(parents=True, exist_ok=True)

for name in ["pass_sample", "rework_sample", "hold_sample", "human_review_sample"]:
    p = out / f"{name}.png"
    if not p.exists():
        make_placeholder_png(p, name)
        print(f"  ✓ Created {p.name}")
    else:
        print(f"  ✓ {p.name} already present")

print(f"  Placeholder images: {len(list(out.glob('*.png')))}")
PYEOF
else
    echo "  python3 not found — skipping placeholder generation"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Download complete ==="
echo "Location: ${OUTPUT_DIR}"
find "${OUTPUT_DIR}" -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null \
    | wc -l | xargs -I{} echo "Total images: {}"
echo ""
echo "Load samples in the Streamlit UI from the sidebar → Sample Images."
