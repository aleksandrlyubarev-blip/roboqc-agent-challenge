# GradeLens — H0 hackathon plan (Amazon track)

**Working name:** GradeLens — AI condition grading for used electronics.
**One-liner:** Photograph a used phone/laptop, get an instant, dispute-ready
condition report — defects, an A–D cosmetic grade, and a resale price band.

GradeLens is a near-direct port of the **NeuroVision Display** machinery (display /
device defect detection + Claude Fable 5 structured reasoning) onto consumer
devices. The hard part — a vision + reasoning pipeline that emits a structured,
defensible defect report — already exists in this repo (`src/neuron_vision/fable5/`).
H0 repackages it as a monetizable B2C/B2B web product on the required stack.

## Why this idea

- **Profile fit (max).** Founder background is electronics/display QC (RoboQC SMT
  first-article inspection; NeuroVision Display panel-defect inspection). Device
  grading is the same defect taxonomy (mura, dead pixels, scratches, dents,
  cracks) applied to phones/laptops.
- **Machinery reuse (~80%).** System-prompt design, schema sanitizer, structured
  output, refusal→Opus-4.8 fallback, cost telemetry — all carry over. The TS port
  lives in `apps/gradelens/lib/grading/`; the Python reference stays in
  `src/neuron_vision/fable5/`.
- **B2C feel of variant B, kept.** A Yad2 / Back Market seller scans their phone
  before listing → honest grade report they can attach; a buyer verifies a
  listing. Consumer-facing, monetizable, demos in 30 seconds.
- **Market.** Refurbisher/repair-shop grading (NSYS, Phonecheck, Piceasoft) is
  enterprise-priced and hardware-tethered. Small refurbishers, repair shops, and
  private sellers have no phone-camera, no-hardware grader. That's the wedge.

## H0 requirements → how we satisfy them

| H0 requirement | GradeLens |
| --- | --- |
| AWS database | **DynamoDB** single-table (`gradelens` table) — grading records + GSI for user history |
| AWS (storage) | **S3** for uploaded device photos (presigned PUT from the browser) |
| Vercel v0 / Next.js | Next.js App Router on Vercel; UI generated/iterated with v0 |
| Monetizable B2C/B2B | Free first report → pay-per-report ($1.99) or shop SaaS ($49–99/mo) |
| Reasoning engine | **Claude Fable 5** (`claude-fable-5`) vision + structured output, fallback `claude-opus-4-8` |

> **Credits form deadline: June 26, 2026** — submit for $100 AWS + $30 v0 credits.
> **Submission deadline: June 29, 2026, 5pm PDT.**

## Architecture

```
Browser (Next.js / Vercel)
  │  1. request presigned S3 URL ───────────► /api/upload-url ──► S3 (PUT direct)
  │  2. POST photo refs + device hint ──────► /api/grade
  │                                              │
  │                                              ├─ fetch images from S3
  │                                              ├─ Claude Fable 5 (vision + json_schema,
  │                                              │   fallback → Opus 4.8 on refusal)
  │                                              ├─ Zod re-validate + derive grade/price
  │                                              └─ write GradingRecord ──► DynamoDB
  │  3. render report + shareable link ◄───── GradingRecord
```

- **No separate Python service.** Everything runs in Next.js Route Handlers on
  Vercel serverless. The GCP Cloud Run / Vertex track (the original ТЗ, in
  `infra/fable5/` + `docs/fable5_integration.md`) stays as the NeuroVision
  enterprise deployment — GradeLens is the standalone consumer product.
- **Secrets:** `ANTHROPIC_API_KEY` via Vercel env (encrypted), never in code. AWS
  via Vercel env or an OIDC role. Same discipline as the GCP track.

### DynamoDB single-table design (`gradelens`)

| Entity | PK | SK | GSI1PK | GSI1SK |
| --- | --- | --- | --- | --- |
| Grading record | `GRADING#<id>` | `META` | `USER#<userId>` | `<createdAt>` |

One item per grading session holds input refs, the model output, derived grade,
price band, and call metadata (model id, fallback used, latency, tokens, cost).
GSI1 lists a user's history newest-first. On-demand billing; no capacity to tune.

## 16-day plan (today = Jun 13 → Jun 29)

| Day | Milestone |
| --- | --- |
| 1 (done) | Idea locked; scaffold (`apps/gradelens/`): grading core (TS port), DynamoDB + S3 libs, `/api/grade` + `/api/upload-url`, landing/scan UI, CloudFormation table |
| 2 | `npm i`, local run; wire real S3 presign + DynamoDB (LocalStack or real); end-to-end one device with a real Anthropic key |
| 3 | v0: polish scan flow (multi-angle capture guidance), report view, A–D grade badge, price band |
| 4 | Shareable read-only report page (`/r/<id>`); copy-link + PDF export |
| 5 | AWS deploy: real DynamoDB table + S3 bucket + IAM; Vercel project + env; **submit credits form by Jun 26** |
| 6–7 | Grade calibration: 15–20 real device photo sets; tune system prompt + grade thresholds; add device-category-specific checks (laptop hinge, phone screen) |
| 8 | B2B mode: batch upload for a repair shop; CSV export of grades |
| 9 | Auth (lightweight — email magic link or anonymous device id); user history via GSI1 |
| 10 | Monetization stub: free-first-report gate + Stripe test checkout for pay-per-report |
| 11 | Cost/latency telemetry surfaced; rate limiting; error states |
| 12 | Hardening: input validation, S3 content-type/size limits, abuse guards |
| 13 | Demo script + 2–3 hero device sets; record the 30-sec "scan → report" flow |
| 14 | Devpost write-up; architecture diagram; AWS+Vercel integration evidence |
| 15 | Buffer / polish / dry-run the live demo |
| 16 (Jun 29) | Final submission before 5pm PDT |

## Monetization

- **B2C pay-per-report:** first report free, then $1.99/report (proves on Proofr's
  $9.90/mo consumer price point in the adjacent vehicle space).
- **B2B shop SaaS:** $49–99/mo for unlimited grading + batch + CSV export for
  repair shops / small refurbishers.
- **API (later):** per-grade pricing for marketplaces (Yad2-style) to embed a
  "verified condition" badge.

## Demo script (judges)

1. Hold up a real, visibly-scuffed phone. Take 4 photos (front, back, corners).
2. Tap **Grade** → ~10–20s → structured report: detected device, defect list with
   severity, **Grade B**, rationale, **resale band ₪X–₪Y**, limitations note.
3. Tap **Share** → open the read-only report link (this is what a seller attaches
   to a listing).
4. Switch to **Shop mode** → batch of 5 devices graded → CSV export.

The "why you" answer: the inspection + LLM-reasoning pipeline is the hard part and
it already exists (NeuroVision) — judges see a working, calibrated grader, not a
prompt wrapper.

## Open items / risks

- Photos can't verify battery health or internal components — the report says so
  explicitly (`confidenceNote`); position as **cosmetic + observable**, not a full
  diagnostic.
- Grade calibration is the real work (days 6–7) — needs a small labeled set.
- Stripe + auth are stubs; keep them optional so the demo never depends on them.
