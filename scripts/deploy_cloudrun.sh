#!/usr/bin/env bash
#
# deploy_cloudrun.sh — one-command Cloud Run deploy for Neuron Vision Display.
#
# Builds the container with Cloud Build and deploys the Streamlit app to
# Cloud Run, reading configuration from the local .env file.
#
# Usage:
#   ./scripts/deploy_cloudrun.sh
#
# Prerequisites:
#   - gcloud CLI authenticated (`gcloud auth login`)
#   - Docker installed (for `gcloud auth configure-docker`)
#   - Vertex AI API enabled on the target project
#   - A .env file with GOOGLE_CLOUD_PROJECT set (see .env.example)

set -euo pipefail

# ── Resolve repo root so the script works from any directory ──────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# ── Configuration ─────────────────────────────────────────────────────────────
SERVICE="neuron-vision-display"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
MIN_INSTANCES="${MIN_INSTANCES:-1}"
CONCURRENCY="${CONCURRENCY:-4}"

# ── 1. Load .env ──────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env and set GOOGLE_CLOUD_PROJECT." >&2
  exit 1
fi

# Export every non-comment, non-blank assignment from .env into the environment.
set -a
# shellcheck disable=SC1091
source .env
set +a

# Allow .env to override the region default.
REGION="${GOOGLE_CLOUD_REGION:-${REGION}}"

if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" || "${GOOGLE_CLOUD_PROJECT}" == "your-gcp-project-id" ]]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT is not set to a real project in .env." >&2
  exit 1
fi

IMAGE="gcr.io/${GOOGLE_CLOUD_PROJECT}/${SERVICE}"

echo ">>> Project : ${GOOGLE_CLOUD_PROJECT}"
echo ">>> Region  : ${REGION}"
echo ">>> Image   : ${IMAGE}"
echo ">>> Min inst: ${MIN_INSTANCES}"
echo ">>> Concur. : ${CONCURRENCY}"
echo

# ── 2. Configure Docker auth for Container Registry ───────────────────────────
echo ">>> Configuring Docker auth for gcr.io ..."
gcloud auth configure-docker --quiet

# ── 3. Build and push the image with Cloud Build ──────────────────────────────
echo ">>> Building image with Cloud Build ..."
gcloud builds submit \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --tag "${IMAGE}" \
  .

# ── 4. Deploy to Cloud Run ────────────────────────────────────────────────────
ENV_VARS="GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_REGION=${REGION},DEMO_MODE=0"
if [[ -n "${PHOENIX_COLLECTOR_ENDPOINT:-}" ]]; then
  ENV_VARS="${ENV_VARS},PHOENIX_COLLECTOR_ENDPOINT=${PHOENIX_COLLECTOR_ENDPOINT}"
fi
if [[ -n "${PHOENIX_API_KEY:-}" ]]; then
  ENV_VARS="${ENV_VARS},PHOENIX_API_KEY=${PHOENIX_API_KEY}"
fi

echo ">>> Deploying ${SERVICE} to Cloud Run ..."
gcloud run deploy "${SERVICE}" \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --concurrency "${CONCURRENCY}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "${ENV_VARS}"

# ── 5. Print the service URL ──────────────────────────────────────────────────
URL="$(gcloud run services describe "${SERVICE}" \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --region="${REGION}" \
  --format='value(status.url)')"

echo
echo ">>> Deployed successfully."
echo ">>> Service URL: ${URL}"
