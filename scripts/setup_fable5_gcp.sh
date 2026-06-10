#!/usr/bin/env bash
#
# setup_fable5_gcp.sh — one-command GCP bootstrap + deploy for the Fable 5
# reasoning service (NeuroVision Display / RomeoFlexVision).
#
# Run this ONCE when GCP access and the Anthropic API key are available:
#   ANTHROPIC_KEY_VALUE='sk-ant-...' ./scripts/setup_fable5_gcp.sh
#
# Reads GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_REGION from .env (same convention
# as deploy_cloudrun.sh). Idempotent: safe to re-run — existing resources are
# kept, the secret gets a new version, and the service is redeployed.
#
# What it does (details: docs/fable5_integration.md):
#   1. Enables the required APIs
#   2. Stores the Anthropic key in Secret Manager (secret: anthropic-api-key)
#   3. Creates the fable5-runner service account with access to ONLY that secret
#   4. Creates the Artifact Registry repo `neuron-vision`
#   5. Builds + deploys via Cloud Build (infra/fable5/cloudbuild.yaml)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# ── 1. Load .env ──────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env and set GOOGLE_CLOUD_PROJECT." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SECRET_ID="${ANTHROPIC_SECRET_ID:-anthropic-api-key}"
SA_NAME="fable5-runner"
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
REPO_NAME="neuron-vision"

if [[ -z "${PROJECT}" || "${PROJECT}" == "your-gcp-project-id" ]]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT is not set to a real project in .env." >&2
  exit 1
fi

echo ">>> Project : ${PROJECT}"
echo ">>> Region  : ${REGION}"
echo ">>> Secret  : ${SECRET_ID}"
echo

# ── 2. Enable APIs ────────────────────────────────────────────────────────────
echo ">>> Enabling required APIs ..."
gcloud services enable \
  secretmanager.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project "${PROJECT}"

# ── 3. Anthropic key → Secret Manager ────────────────────────────────────────
# The key is read from ANTHROPIC_KEY_VALUE (env only, never argv — argv leaks
# into `ps` and shell history).
if gcloud secrets describe "${SECRET_ID}" --project "${PROJECT}" >/dev/null 2>&1; then
  echo ">>> Secret ${SECRET_ID} exists."
  if [[ -n "${ANTHROPIC_KEY_VALUE:-}" ]]; then
    echo ">>> Adding a new secret version ..."
    printf '%s' "${ANTHROPIC_KEY_VALUE}" | gcloud secrets versions add "${SECRET_ID}" \
      --data-file=- --project "${PROJECT}"
  fi
else
  if [[ -z "${ANTHROPIC_KEY_VALUE:-}" ]]; then
    echo "ERROR: secret ${SECRET_ID} does not exist and ANTHROPIC_KEY_VALUE is not set." >&2
    echo "Usage: ANTHROPIC_KEY_VALUE='sk-ant-...' $0" >&2
    exit 1
  fi
  echo ">>> Creating secret ${SECRET_ID} ..."
  printf '%s' "${ANTHROPIC_KEY_VALUE}" | gcloud secrets create "${SECRET_ID}" \
    --replication-policy=automatic --data-file=- --project "${PROJECT}"
fi

# ── 4. Service account with least privilege ──────────────────────────────────
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project "${PROJECT}" >/dev/null 2>&1; then
  echo ">>> Creating service account ${SA_NAME} ..."
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="Fable 5 reasoning service" --project "${PROJECT}"
fi
echo ">>> Granting secretAccessor on ${SECRET_ID} only ..."
gcloud secrets add-iam-policy-binding "${SECRET_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --project "${PROJECT}" >/dev/null

# ── 5. Artifact Registry ──────────────────────────────────────────────────────
if ! gcloud artifacts repositories describe "${REPO_NAME}" \
    --location "${REGION}" --project "${PROJECT}" >/dev/null 2>&1; then
  echo ">>> Creating Artifact Registry repo ${REPO_NAME} ..."
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker --location "${REGION}" --project "${PROJECT}"
fi

# ── 6. Build + deploy ─────────────────────────────────────────────────────────
echo ">>> Building and deploying via Cloud Build ..."
gcloud builds submit \
  --config infra/fable5/cloudbuild.yaml \
  --substitutions "_REGION=${REGION},_SECRET_ID=${SECRET_ID}" \
  --project "${PROJECT}"

URL=$(gcloud run services describe fable5-reasoning \
  --region "${REGION}" --project "${PROJECT}" --format='value(status.url)')
echo
echo ">>> Deployed: ${URL}"
echo ">>> Smoke test: ./scripts/smoke_fable5.sh"
