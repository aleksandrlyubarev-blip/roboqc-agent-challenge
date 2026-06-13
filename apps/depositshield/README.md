# DepositShield

Photograph a rental at move-in or move-out → a structured **condition report**
that organizes visual evidence and classifies **normal wear vs. damage beyond
normal wear**, with a draft responsibility hint per finding.

> DepositShield **organizes visual evidence and drafts a condition report.** It is
> **not** legal advice, not a forensic determination, and makes **no promise** about
> deposit recovery. This framing is intentional and appears throughout the UI.

The Amazon **H0** entry: Next.js on Vercel + AWS (DynamoDB + S3) + **Claude Fable 5**.
Decision rationale and scoring: [`docs/H0_IDEATION.md`](../../docs/H0_IDEATION.md).

## Why this scores on H0

- **Technical Implementation:** a real data model, not a toy. DynamoDB is an
  audit/event store — session meta + per-photo events + report — queryable as a
  full trail per inspection.
- **Reasoning, not just detection:** `wear_classification` + draft responsibility
  is where Claude Fable 5 visibly beats pixel-only CV (it reasons "who, and why",
  with caveats). Server-side fallback to `claude-opus-4-8` on a safety refusal.
- **Demo strength:** create session → upload room photos → room-by-room report →
  shareable link, in well under 3 minutes.

Shares the proven reasoning design with the repo's NeuroVision pipeline
(`src/neuron_vision/fable5/`); ported to TypeScript in `lib/inspection/`.

## 48-hour milestone (the go/no-go gate)

Working flow by **Jun 15–17**: *create session → upload photo → get report →
record in DynamoDB*. If it isn't working by then, pivot back to RoboQC Cloud (the
safe profile-fit fallback). Everything in this scaffold targets that flow.

**In MVP:** Vercel app · property/session · photo upload · apartment defect
taxonomy · grouped (room-by-room) findings · DynamoDB persistence · report page ·
shareable evidence report.
**Cut from MVP:** Stripe · full auth · PDF export · mobile-native camera · real
forensic before/after diff · legal workflow · any deposit-recovery promise.

## Layout

```
app/
  page.tsx                       create session → upload → report (client)
  r/[id]/page.tsx                shareable, server-rendered report
  api/upload-url/                POST → presigned S3 PUT
  api/sessions/                  POST create · GET list (GSI1)
  api/sessions/[id]/             GET full session bundle (audit trail)
  api/sessions/[id]/report/      POST photoKeys → Fable 5 inspection → DynamoDB
lib/
  inspection/client.ts           Fable 5 vision + json_schema + Opus fallback
  inspection/schema.ts           wire schema (constraint-free) + zod validator
  inspection/prompt.ts           cautious, cache-friendly system prompt
  db/dynamo.ts                   single-table audit/event store
  storage/s3.ts                  presign + server-side fetch→base64
components/Report.tsx            shared presentational report
infra/dynamodb-table.yaml        CloudFormation: table + S3 bucket
```

## Local dev

```bash
cd apps/depositshield
cp .env.example .env.local      # ANTHROPIC_API_KEY + AWS values
npm install
npm run dev                     # http://localhost:3000
```

`npm run typecheck` runs `tsc --noEmit`. Needs a `@anthropic-ai/sdk` that supports
Fable 5 + the `server-side-fallback-2026-06-01` beta.

## Provision AWS

```bash
aws cloudformation deploy \
  --template-file infra/dynamodb-table.yaml \
  --stack-name depositshield \
  --parameter-overrides BucketName=depositshield-uploads-<unique> \
  --capabilities CAPABILITY_NAMED_IAM
```

Set `DEPOSITSHIELD_TABLE`, `DEPOSITSHIELD_BUCKET`, `AWS_REGION` to match.

## Deploy to Vercel

1. New Vercel project, **Root Directory = `apps/depositshield`**.
2. Encrypted env: `ANTHROPIC_API_KEY`, `AWS_REGION`, `DEPOSITSHIELD_TABLE`,
   `DEPOSITSHIELD_BUCKET`, AWS creds (prefer a Vercel↔AWS OIDC role).
3. Tighten S3 CORS `AllowedOrigins` to the Vercel domain before launch.

## Key dates (H0)

- Submission: **Jun 29 2026, 5pm PDT** (= Jun 30, 03:00 IDT).
- Credits form ($100 AWS + $30 v0): **by Jun 26 2026, 22:00 IDT**.
- Verify the existing-project eligibility rule before submitting — we present this
  as a new app on a new stack, which reduces that risk.

## Security

- `ANTHROPIC_API_KEY` and AWS creds live only in env (Vercel encrypted /
  `.env.local`), never in code or the repo.
- The inspection client logs metadata only — never prompts, images, or output.
- S3 bucket blocks public access; photos reached only via presigned URLs and
  expire after 30 days.
