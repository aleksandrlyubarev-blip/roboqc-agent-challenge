# GradeLens

AI condition grading for used electronics. Photograph a phone/laptop → instant,
dispute-ready condition report: defects, an **A–D cosmetic grade**, and a resale
price band. Built for the Amazon **H0** hackathon (Next.js on Vercel + AWS
DynamoDB/S3 + Claude Fable 5).

Product plan and 16-day schedule: [`docs/h0_gradelens_plan.md`](../../docs/h0_gradelens_plan.md).

## Stack

- **Next.js (App Router)** on Vercel — UI + serverless Route Handlers
- **Claude Fable 5** (`claude-fable-5`) vision + structured output, server-side
  fallback to `claude-opus-4-8` on a safety refusal
- **AWS DynamoDB** — single-table grading records (GSI1 for user history)
- **AWS S3** — device photos, uploaded via presigned PUT direct from the browser
- **zod** — re-validates the model's JSON against `GradingResultSchema`

This is the consumer port of the repo's NeuroVision Display pipeline
(`src/neuron_vision/fable5/`); the grading core in `lib/grading/` mirrors
`Fable5Client` / its Pydantic schemas in TypeScript.

## Layout

```
app/
  page.tsx              scan → report UI (client)
  api/upload-url/       POST → presigned S3 PUT
  api/grade/            POST photoKeys → Fable 5 grade → DynamoDB
  api/devices/          GET  → user grading history (GSI1)
lib/
  grading/client.ts     Fable 5 call: vision + json_schema + Opus fallback
  grading/schema.ts     wire JSON schema (constraint-free) + zod validator
  grading/prompt.ts     byte-stable, cache-friendly system prompt
  db/dynamo.ts          single-table access
  storage/s3.ts         presign + server-side fetch→base64 for the model
infra/gradelens/        CloudFormation: DynamoDB table + S3 bucket
```

## Local dev

```bash
cd apps/gradelens
cp .env.example .env.local      # fill ANTHROPIC_API_KEY + AWS values
npm install
npm run dev                     # http://localhost:3000
```

`npm run typecheck` runs `tsc --noEmit`. Requires a `@anthropic-ai/sdk` version
that supports Fable 5 + the `server-side-fallback-2026-06-01` beta; bump it if
`fallbacks`/`output_config` aren't recognized.

## Provision AWS

```bash
aws cloudformation deploy \
  --template-file infra/gradelens/dynamodb-table.yaml \
  --stack-name gradelens \
  --parameter-overrides BucketName=gradelens-uploads-<unique> \
  --capabilities CAPABILITY_NAMED_IAM
```

Set `GRADELENS_TABLE`, `GRADELENS_BUCKET`, and `AWS_REGION` to match.

## Deploy to Vercel

1. New Vercel project, **Root Directory = `apps/gradelens`**.
2. Add encrypted env vars: `ANTHROPIC_API_KEY`, `AWS_REGION`, `GRADELENS_TABLE`,
   `GRADELENS_BUCKET`, and AWS credentials (prefer a Vercel↔AWS OIDC role over
   long-lived keys).
3. Tighten the S3 CORS `AllowedOrigins` to the Vercel domain before launch.

## Security

- `ANTHROPIC_API_KEY` and AWS creds live only in env (Vercel encrypted / `.env.local`),
  never in code or the repo.
- The grading client logs metadata only — never prompts, images, or model output.
- S3 bucket blocks all public access; photos are reached only via presigned URLs
  and expire after 30 days.
