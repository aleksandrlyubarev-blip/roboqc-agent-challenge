#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
ALERT_EMAIL="${ALERT_EMAIL:?Set ALERT_EMAIL=you@example.com}"
SERVICE_NAME="${SERVICE_NAME:-roboqc-agent}"
LLM_ERROR_THRESHOLD_COUNT="${LLM_ERROR_THRESHOLD_COUNT:-5}"
HTTP_5XX_THRESHOLD_COUNT="${HTTP_5XX_THRESHOLD_COUNT:-5}"

HERE="$(cd "$(dirname "$0")" && pwd)"

gcloud config set project "${PROJECT_ID}" >/dev/null

upsert_metric() {
  local name="$1"
  local config_file="$2"
  local rendered_config
  rendered_config="$(mktemp)"
  sed "s/service_name=\"roboqc-agent\"/service_name=\"${SERVICE_NAME}\"/" \
    "${config_file}" >"${rendered_config}"

  if gcloud logging metrics describe "${name}" >/dev/null 2>&1; then
    echo "    metric ${name} exists; updating"
    gcloud logging metrics update "${name}" \
      --config-from-file="${rendered_config}"
  else
    echo ">>> Creating metric ${name}"
    gcloud logging metrics create "${name}" \
      --config-from-file="${rendered_config}"
  fi
  rm -f "${rendered_config}"
}

upsert_metric roboqc_llm_latency_ms "${HERE}/llm-latency-metric.yaml"
upsert_metric roboqc_llm_error_count "${HERE}/llm-error-metric.yaml"
upsert_metric roboqc_http_5xx_count "${HERE}/http-5xx-metric.yaml"

CHANNEL_NAME="$(gcloud monitoring channels list \
  --filter="type=email AND labels.email_address=${ALERT_EMAIL}" \
  --format='value(name)' 2>/dev/null | head -n1 || true)"

if [[ -z "${CHANNEL_NAME}" ]]; then
  echo ">>> Creating email notification channel for ${ALERT_EMAIL}"
  CHANNEL_NAME="$(gcloud monitoring channels create \
    --display-name="RoboQC alerts (${ALERT_EMAIL})" \
    --type=email \
    --channel-labels="email_address=${ALERT_EMAIL}" \
    --format='value(name)')"
else
  echo "    notification channel exists: ${CHANNEL_NAME}"
fi

render_policy() {
  local src="$1"
  local threshold="$2"
  python3 - "${src}" "${threshold}" "${CHANNEL_NAME}" <<'PY'
import json
import sys

src, threshold, channel = sys.argv[1:]
with open(src) as f:
    policy = json.load(f)
policy["conditions"][0]["conditionThreshold"]["thresholdValue"] = float(threshold)
policy["notificationChannels"] = [channel]
print(json.dumps(policy, indent=2))
PY
}

upsert_policy() {
  local display_name="$1"
  local rendered_json="$2"
  local tmp
  tmp="$(mktemp)"
  printf '%s\n' "${rendered_json}" >"${tmp}"

  local existing
  existing="$(gcloud monitoring policies list \
    --filter="displayName:'${display_name}'" \
    --format='value(name)' 2>/dev/null | head -n1 || true)"

  if [[ -n "${existing}" ]]; then
    echo "    policy '${display_name}' exists; updating"
    gcloud monitoring policies update "${existing}" --policy-from-file="${tmp}"
  else
    echo ">>> Creating policy '${display_name}'"
    gcloud monitoring policies create --policy-from-file="${tmp}"
  fi

  rm -f "${tmp}"
}

LLM_POLICY="$(render_policy \
  "${HERE}/llm-error-alert.policy.json" \
  "${LLM_ERROR_THRESHOLD_COUNT}")"
upsert_policy "RoboQC — LLM error rate (>5 / 5 min)" "${LLM_POLICY}"

HTTP_POLICY="$(render_policy \
  "${HERE}/http-5xx-alert.policy.json" \
  "${HTTP_5XX_THRESHOLD_COUNT}")"
upsert_policy "RoboQC — HTTP 5xx rate (>5 / 5 min)" "${HTTP_POLICY}"

echo
echo ">>> Monitoring setup complete."
echo "    Metrics: roboqc_llm_latency_ms, roboqc_llm_error_count, roboqc_http_5xx_count"
echo "    Channel: ${CHANNEL_NAME}"
