# Monitoring

This directory contains the submission-safe observability artifacts for the
Cloud Run service.

## Signals

| Signal | Source log | Why it matters |
|---|---|---|
| `roboqc_llm_latency_ms` | `event="llm_call"` | multimodal latency drift during tile inspection |
| `roboqc_llm_error_count` | `event="llm_error"` | provider failures, bad credentials, quota issues |
| `roboqc_http_5xx_count` | `event="http_request"` + `status_code >= 500` | API failures visible to the operator UI |
| `roboqc_fable5_fallback_count` | `event="fable5_fallback"` | Fable 5 -> Opus 4.8 degradations (refusals, rate limits, transport) |

The current Vertex telemetry emits token counts and latency, but not normalized
USD cost. A cost metric is therefore intentionally deferred until the provider
surface has a real pricing-normalization step instead of a guessed field.

## Apply

```bash
PROJECT_ID="your-project" \
ALERT_EMAIL="you@example.com" \
bash infra/monitoring/setup.sh
```

Optional overrides:

- `SERVICE_NAME` — defaults to `roboqc-agent`
- `LLM_ERROR_THRESHOLD_COUNT` — defaults to `5` errors per 5 minutes
- `HTTP_5XX_THRESHOLD_COUNT` — defaults to `5` responses per 5 minutes

Threshold tuning guidance: on a quiet line, 5 errors / 5 min catches real
incidents without paging on single retried blips; for high-volume production
raise the thresholds (or switch the policies to a rate-based condition) so the
alert tracks error *rate*, not absolute count.

The setup script is idempotent: it creates or updates the four log-based
metrics, reuses an existing email notification channel when present, and
creates or updates both alert policies.

## Budget guardrail

Until per-request USD cost lands in telemetry, use a billing budget as the
spend guardrail (one-time setup, requires the Billing Account Administrator
role):

```bash
gcloud billing budgets create \
  --billing-account="${BILLING_ACCOUNT_ID}" \
  --display-name="RoboQC monthly" \
  --budget-amount=1000USD \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.8 \
  --threshold-rule=percent=1.0
```

## Why no cost alert yet?

The old donor stack received `cost_usd` from LiteLLM. RoboQC uses the Vertex
Gemini provider directly, and its current public telemetry contract emits model,
operation, latency, request id, and token counts. Monitoring should track the
fields the code actually emits. Cost alerts return once we add a trustworthy
pricing-normalization layer.
