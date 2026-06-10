#!/usr/bin/env bash
#
# smoke_fable5.sh — post-deploy smoke test for the Fable 5 reasoning service.
#
# Usage:
#   ./scripts/smoke_fable5.sh                  # against the deployed Cloud Run service
#   FABLE5_URL=http://localhost:8080 ./scripts/smoke_fable5.sh   # against a local run
#
# Local run (with ANTHROPIC_API_KEY exported):
#   PYTHONPATH=src uvicorn neuron_vision.fable5.api:app --port 8080

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -z "${FABLE5_URL:-}" ]]; then
  if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
  REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
  FABLE5_URL=$(gcloud run services describe fable5-reasoning \
    --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" --format='value(status.url)')
  AUTH_HEADER="Authorization: Bearer $(gcloud auth print-identity-token)"
else
  AUTH_HEADER=""
fi

echo ">>> Target: ${FABLE5_URL}"

echo ">>> 1/2 healthz ..."
curl -fsS ${AUTH_HEADER:+-H "${AUTH_HEADER}"} "${FABLE5_URL}/healthz"
echo

echo ">>> 2/2 analyze-defect (sample payload) ..."
curl -fsS -X POST "${FABLE5_URL}/analyze-defect" \
  ${AUTH_HEADER:+-H "${AUTH_HEADER}"} \
  -H "Content-Type: application/json" \
  --data @data/fable5_sample_request.json | python3 -m json.tool

echo
echo ">>> Smoke test passed."
