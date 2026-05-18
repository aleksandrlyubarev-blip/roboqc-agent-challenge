# Cloud Run deployment

This directory contains the submission-safe Cloud Run scaffold for RoboQC.

## Why the service is intentionally small

Week 1 only needs a verified deployment shell around the API process:

- Python 3.11 container
- `/healthz` startup probe target
- region default `us-central1`
- one request per instance for predictable Gemini demo behavior
- Cloud Run IAM at the platform boundary (`--no-allow-unauthenticated`)

The four-agent graph and Streamlit surface land on top of this service later.
There is deliberately no app-level API-key middleware in v1; the public
architecture already fixes auth at Cloud Run IAM + service account.

## Deploy

```bash
PROJECT_ID="your-project" \
SERVICE_ACCOUNT="roboqc-agent@your-project.iam.gserviceaccount.com" \
bash infra/cloudrun/deploy.sh
```

Optional overrides:

- `REGION` — defaults to `us-central1`
- `SERVICE` — defaults to `roboqc-agent`
- `REPOSITORY` — defaults to `roboqc`
- `TAG` — defaults to the current Git SHA

`service.yaml` is a reviewable template for the same runtime shape when a
declarative deploy is preferred.
