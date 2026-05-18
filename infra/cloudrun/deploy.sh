#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-roboqc-agent}"
REPOSITORY="${REPOSITORY:-roboqc}"
TAG="${TAG:-$(git rev-parse --short HEAD)}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:?Set SERVICE_ACCOUNT}"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE}:${TAG}"

echo ">>> Building image ${IMAGE}"
gcloud builds submit \
  --project="${PROJECT_ID}" \
  --config=infra/cloudrun/cloudbuild.yaml \
  --substitutions="_IMAGE=${IMAGE}" \
  .

echo ">>> Deploying ${SERVICE} to Cloud Run in ${REGION}"
gcloud run deploy "${SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --platform=managed \
  --execution-environment=gen2 \
  --image="${IMAGE}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --cpu=1 \
  --memory=512Mi \
  --concurrency=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=300 \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},VERTEX_LOCATION=${REGION}"

URL="$(gcloud run services describe "${SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)')"

echo
echo ">>> Deployed: ${URL}"
echo ">>> Health check: ${URL}/healthz"
