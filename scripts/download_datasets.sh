#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT_DIR}/data"
CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/.cache/datasets}"

DEEPPCB_DIR="${DATA_DIR}/deeppcb"
VISA_PCB_DIR="${DATA_DIR}/visa_pcb"
VISA_ARCHIVE="${CACHE_DIR}/VisA_20220922.tar"
VISA_URL="https://amazon-visual-anomaly.s3.us-west-2.amazonaws.com/VisA_20220922.tar"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

download_deeppcb() {
  if [[ -d "${DEEPPCB_DIR}/PCBData" ]]; then
    echo ">>> DeepPCB already present: ${DEEPPCB_DIR}"
    return
  fi

  if [[ -e "${DEEPPCB_DIR}" ]]; then
    echo "DeepPCB target exists but is incomplete: ${DEEPPCB_DIR}" >&2
    echo "Remove or repair it before rerunning this script." >&2
    exit 1
  fi

  echo ">>> Cloning official DeepPCB repository"
  git clone --depth 1 https://github.com/tangsanli5201/DeepPCB.git "${DEEPPCB_DIR}"
}

download_visa_pcb_subset() {
  if [[ -d "${VISA_PCB_DIR}/pcb1" && -d "${VISA_PCB_DIR}/pcb2" \
    && -d "${VISA_PCB_DIR}/pcb3" && -d "${VISA_PCB_DIR}/pcb4" ]]; then
    echo ">>> VisA PCB subset already present: ${VISA_PCB_DIR}"
    return
  fi

  mkdir -p "${CACHE_DIR}" "${VISA_PCB_DIR}"

  if [[ ! -f "${VISA_ARCHIVE}" ]]; then
    echo ">>> Downloading official VisA archive"
    curl -L "${VISA_URL}" -o "${VISA_ARCHIVE}"
  fi

  echo ">>> Extracting VisA pcb1-pcb4 subset"
  tar -xf "${VISA_ARCHIVE}" \
    -C "${VISA_PCB_DIR}" \
    --strip-components=1 \
    VisA/pcb1 VisA/pcb2 VisA/pcb3 VisA/pcb4
}

explain_pku_hold() {
  cat <<'EOF'
>>> PKU-Market-PCB is intentionally not downloaded.
    Primary-source license terms are not yet recorded in data/CITATIONS.md.
    Add it only after that verification is complete.
EOF
}

main() {
  require_command git
  require_command curl
  require_command tar

  mkdir -p "${DATA_DIR}"
  download_deeppcb
  download_visa_pcb_subset
  explain_pku_hold

  echo ">>> Dataset preparation complete"
}

main "$@"
