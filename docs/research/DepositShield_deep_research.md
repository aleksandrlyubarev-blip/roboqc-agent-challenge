# DepositShield — Deep Research & Feasibility Report

*Date: 2026-06-13. Synthesis of 5 parallel research streams (legal/liability,
privacy+Israel, market/competition, capture-fidelity/LLM-accuracy, evidence/MVP).
Sources cited inline. Confidence flagged. This is research, NOT legal advice —
items marked "lawyer-confirm" need local counsel before launch.*

---

## Executive recommendation — BUILD, NARROWED

**Build it — but narrow the product and change one feature.** The core function —
*organize dated visual evidence into a structured condition report* — is **low
legal risk and squarely aligned with what every studied jurisdiction treats as
decisive evidence** (UK deposit schemes, California's new AB 2801, New York,
Germany's Übergabeprotokoll, and Israel's Fair Rental Law, where the
normal-wear-vs-damage call is legally decisive and "dated photos + entry protocol"
are literally what small-claims judges ask for). There is a **real market gap**:
the space is crowded with photo+checklist documentation tools and a growing tier
of CV *damage-detectors*, but almost nobody ships the **reasoning layer** — a
report that argues normal-wear-vs-damage against a legal standard.

Two non-negotiable changes fall out of the research:

1. **Neuter the "responsibility hint."** Naming a responsible party ("tenant is
   liable") applies a legal standard to specific facts = the textbook definition of
   legal advice / UPL, and ignores the *betterment* and *apportionment* doctrines
   that make flat responsibility calls frequently **wrong as a matter of law**. A
   live suit (*Nippon Life v. OpenAI*, 2026) targets exactly this pattern, and the
   most authoritative analysis warns **a footer disclaimer may not save you** — the
   safe fix is an *architectural* guardrail that won't state who wins.
2. **Treat the LLM as decision-support, not adjudicator** on the contested
   wear-vs-damage call. Benchmarks put current multimodal models ~75% on general
   anomaly detection and **<25% F1 on condition *severity*** — strong on the easy
   half (a hole, a burn, a big stain), weak on exactly the contested half where
   disputes live. Keep a human-in-the-loop confirm step.

**On the founder's two worries:**
- *"Do we need 3D modelling of the apartment?"* — **No.** Decisive across sources.
  Guided 2D capture is the industry standard and what adjudicators want; 3D buys
  floor plans/measurements but **loses the surface defect detail** that the report
  depends on, needs LiDAR (RoomPlan is iOS-only), and is a 2-week trap. Defer 3D to
  an optional premium "measurements" add-on.
- *"Promising but too complex for 2 weeks"* — **Half right.** The *full* product
  (legal-grade, automated before/after diff, 3D, multi-jurisdiction, redaction,
  evidence-grade chain of custody) is too much for 2 weeks. A **narrowed MVP**
  (one guided-2D flow → AI *draft* condition report → server-timestamped storage →
  exportable/shareable report) is achievable. The complexity you fear comes from
  the parts the research says to **cut**.

---

## Risk register

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| **"Responsibility hint" = UPL / legal advice** (Nippon v. OpenAI 2026; NY SB 7263 would bar AI "substantive legal responses") | High | High (as designed) | Remove the party verdict; describe defect + neutral *factors* (wear, apportionment, lifespan, "an adjudicator decides"). Architectural guardrail, not just a disclaimer. |
| **LLM wrong on contested wear-vs-damage / severity** (<25% F1 on severity; hallucinates added features) | High | High | Frame as draft; human-in-the-loop confirm; never assert a $ figure; run your own eval set before trusting any threshold. |
| **Marketing-induced reliance → negligent-misstatement** (courts may look past disclaimers to over-promising marketing) | High | Med | No "survey/valuation/structural/legal proof/expert/guaranteed recovery" wording. Liability cap + no-third-party-reliance clause + indemnity insurance. |
| **Privacy: incidental capture of faces, mail, documents** (GDPR Art. 9 if face-recognition; Israel Amendment-13, in force Aug 2025) | Med-High | High (homes are full of PII) | No face recognition; auto-blur/redact faces/documents at capture; consent in-app; DPIA; auto-expiry; no-training-by-default. |
| **Unverified phone EXIF timestamp** (trivially editable; "weight collapses" under dispute) | Med | High | Server-side capture timestamp; S3 Object Lock (WORM) + SHA-256 of original. |
| **Partisan single-party report weighted lower** than an independent inventory clerk's | Med | Med | Position as neutral *record-keeper*; emphasize tamper-evident provenance; later: optional independent verification. |
| **Crowded/funded category** (Paraspot — Israeli-rooted, ~$1.3M seed; SnapInspect, Yembo, RentCheck) | Med | High | Differentiate on the *reasoning + local-law-native* layer (Hebrew, פרוטוקול מסירה, small-claims-ready), not "AI inspection" generically. |
| **B2C willingness-to-pay unproven** (abundant free DIY guidance is the competition) | Med | Med | Lead B2B (PM/agency SaaS, proven $5–30/unit/mo); treat B2C per-report as validation-required. |
| **AWS setup time-sink for a 2-week solo build** (IAM/bucket policies) | Med | Med | Keep auth/hosting on Vercel; spend AWS time only on the Object-Lock evidence story; don't hand-roll heavy DynamoDB modeling. |

---

## "Do we need 3D?" — verdict

**No, not for the condition/evidence report.** [Confidence: HIGH]

| | Guided 2D photos | 3D scan (RoomPlan / Matterport / Polycam) |
|---|---|---|
| Surface defects / wear / stains | **Yes — the whole point** | **No** — explicitly loses textures/fine detail |
| Floor plan / area / measurement | No | Yes |
| Device requirement | Any phone camera | LiDAR (RoomPlan iOS-only); ARCore weaker; Matterport $6k hw |
| What adjudicators want | **This** (dated, like-for-like) | Not what they weigh |
| 2-week MVP fit | Yes | Trap (immature; fails on mirrors/glass/thin structures) |

- **MVP capture:** guided room-by-room 2D — checklist + framing/quality nudges +
  per-surface anchor shots + server timestamps. Approximates 3D's "completeness"
  benefit at a fraction of the cost.
- **Real-product capture:** same 2D core, hardened with structured before/after
  pairing (move-in frame as a capture overlay), provenance, dual-party sign-off.
  **Optional LiDAR room-scan as a premium add-on for measurements/floor plans
  only** — never the evidentiary backbone.

Sources: [Apple RoomPlan](https://developer.apple.com/augmented-reality/roomplan/),
[RoomPlan reality check](https://www.it-jim.com/blog/roomplan-framework-by-apple/),
[MMAD ICLR 2025 (~75%)](https://arxiv.org/abs/2410.09453),
[Pavement-severity LLM benchmark (<25% F1)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12900301/),
[AI-damage-from-photos reality](https://rapideyeinspections.com/blog/ai-property-damage-detection-from-photos/).

---

## Recommended 2-week MVP scope

**IN**
- One guided-2D capture flow (room-by-room checklist + framing guidance).
- AI **draft** condition report: defect list + `wear_classification`
  (normal_wear / beyond_normal_wear / unclear) + neutral *factors*
  (apportionment/lifespan/local-law-dependent). **No party verdict, no $ figure.**
- Human-in-the-loop: user reviews/edits before "finalize."
- Server-side capture timestamp; store original in S3 (+ optional Object Lock /
  SHA-256 as the evidence-credibility story); exportable report + shareable link.
- Strong, prominent framing: "organizes visual evidence and drafts a non-binding
  condition report — not legal advice."
- Single-user (managed auth if any); Vercel front end; DynamoDB audit/event store.

**OUT / defer**
- 3D capture; automated before/after *diffing* (manual pairing is fine); naming a
  responsible party; repair-cost estimates; Stripe; multi-party signing/workspaces;
  face/document redaction can be a fast-follow but flag the limitation in the demo.

**3–6 month roadmap (if it proves out)**
1. Evidence hardening: Object Lock + hash + dual-party sign-off + like-for-like
   re-shoot overlay.
2. PII redaction (auto-blur faces/mail/docs); DPIA; consent + privacy notice;
   no-training-by-default.
3. Local-law-native output: Hebrew, פרוטוקול מסירה template, small-claims-ready
   export; align wear logic to published scheme guidance (TDS lifespan tables).
4. B2B path: PM/agency dashboard, portfolio, CSV; explore independent-verification
   tier for evidentiary weight.
5. Optional premium: LiDAR measurements for repaint/area costing.

---

## Competitive landscape

| Vendor | What it does | B2C/B2B | AI? | Notes |
|---|---|---|---|---|
| **Paraspot AI** | Remote tenant scans; CV detects cracks/stains/missing; before/after; claims "wear vs damage" | B2B | Core CV | **Israeli-rooted**, Berlin; ~$1.3–1.5M seed; closest competitor (detection/comparison-led, not reasoning-led) |
| **RentCheck** | Resident-led guided inspections; AI flagging | B2B (1,000+ PMs) | Partial | $3.6M; from ~$5/unit/mo, free ≤10 units |
| **zInspector** | Move-in/out side-by-side; report-from-media | B2B | Partial | Free ≤5; Core $22/mo |
| **Inventory Hive / InventoryBase / Imfuna / Chapps** | UK inventory/check-in-out, dispute-comparison reports | B2B (UK) | Narrow/none | ~£30/mo class; capture+checklist |
| **SnapInspect** | Inspections + AI damage detection + dispatch | B2B | Yes | Demo-led pricing |
| **Yembo** | AI video survey → inventory/3D/floor plans (moving/insurance) | B2B | Strong CV | ~$13.9M; not deposit-focused |
| **HappyCo / ManageCasa / AppFolio / Yardi** | PM-suite inspection modules | B2B (embedded) | Ops AI | Incumbent suites |
| *Properly, Lula, SnagR* | *STR cleaning / maintenance dispatch / construction snagging* | — | — | **Not** condition-report competitors |

**Whitespace:** the **wear-vs-damage *reasoning* report**, and **B2C is nearly
empty** (all credible players are B2B). Most likely paying buyer today = **B2B PMs
/ letting agents** (esp. UK). Sources:
[Paraspot](https://www.paraspot.ai/) · [RentCheck](https://www.getrentcheck.com/) ·
[zInspector](https://www.capterra.com/p/176250/zInspector/) ·
[Inventory Hive](https://www.inventoryhive.co.uk/pricing) ·
[Yembo](https://yembo.ai/).

---

## Jurisdiction cheat-sheet (positioning & disclaimers)

| | Deposit rule | Decisive evidence | Wear-vs-damage | Product note |
|---|---|---|---|---|
| **Israel** | Cap = lower of 3 mo rent / ⅓ lease; return ≤60 days; no withholding for normal wear | Entry protocol + dated photos + quotes (small-claims) — *exactly our artifact* | Live, tenant-tilted distinction (בלאי vs נזק); **no mandatory protocol form = the gap we fill** | Strongest **local** wedge: ~851k rentals, TLV ~49% renters; differentiate Hebrew + small-claims-ready |
| **UK (E&W)** | Protect in TDS/DPS/MyDeposits ≤30 days | **Documentary-only** adjudication; **signed check-in inventory = the #1 doc**; dated photos persuasive | Subjective; **betterment + apportionment** doctrines constrain any "damage" finding | Independent reports weighted higher; partisan single-party = weaker |
| **US — California** | Cap 1 mo (AB 12, 2024); itemize ≤21 days; >$125 needs docs | **AB 2801 (2025): deductions require before/after photos** — a tailwind | Burden on landlord | "Survey/valuation" wording is a UPL/marketing trap |
| **US — New York** | Itemize ≤14 days or forfeit | Optional move-in inspection; itemized statement | Burden on landlord; routine cleaning = wear | State variation is large — no single rule set |
| **Germany** | Kaution ≤3 mo cold rent | **Übergabeprotokoll controls** — unrecorded = uncharged | Normale Abnutzung non-deductible | Contrast: handover protocol is near-absolute evidence |

**Always:** "condition report / visual record," never "survey, valuation,
structural, legal proof, expert evidence, guaranteed deposit recovery." Scope to
visible areas on the imaging date; no-third-party-reliance; "not legal advice."
Sources: [Israel Fair Rental / Kol-Zchut](https://www.kolzchut.org.il/he/%D7%A4%D7%99%D7%A7%D7%93%D7%95%D7%9F_%D7%9E%D7%96%D7%95%D7%9E%D7%9F_%D7%9B%D7%A2%D7%A8%D7%95%D7%91%D7%94_%D7%9C%D7%94%D7%91%D7%98%D7%97%D7%AA_%D7%97%D7%99%D7%95%D7%91) ·
[Israel small-claims evidence](https://pelleg-law.co.il/small-claims-rental-damage-guide/) ·
[UK TDS dispute guide](https://www.propertypassport.uk/guides/tds-tenancy-deposit-scheme-dispute-guide) ·
[CA AB 2801](https://www.hemlane.com/resources/california-security-deposit-laws/) ·
[NY returns](https://ipropertymanagement.com/laws/new-york-security-deposit-returns) ·
[Germany Kaution](https://allaboutberlin.com/guides/mietkaution) ·
[Nippon v. OpenAI (Stanford CodeX)](https://law.stanford.edu/2026/03/07/designed-to-cross-why-nippon-life-v-openai-is-a-product-liability-case/).

---

## Privacy posture (small team, manageable)

A small startup almost certainly sits **below** Israel's database-registration
(>10,000) and mandatory-DPO thresholds at launch. A "**consent + DPIA +
no-training-by-default + auto-expiring photos + no face recognition**" design
aligns with both GDPR and Israel's PPA 2025 AI guidance. **The real engineering
work is redacting incidental PII** (faces, mail, documents) at capture — not the
paperwork. Sources:
[Israel Amendment 13 in force Aug 2025](https://www.loc.gov/item/global-legal-monitor/2025-11-17/israel-amendment-to-privacy-protection-law-goes-into-effect/) ·
[PPA AI guidance](https://www.gornitzky.com/privacy-in-artificial-intelligence-systems-guidelines-of-the-israeli-privacy-protection-authority/) ·
[ICLG Israel 2025-26](https://iclg.com/practice-areas/data-protection-laws-and-regulations/israel).

---

## Open questions / verify before relying

- **Lawyer-confirm:** per-US-state UPL classification of any "responsibility"
  feature; Israeli burden-of-proof allocation in a deposit suit; whether quoting
  repair costs triggers regulated-valuation concerns; enforceability of
  liability-cap / no-reliance clauses against consumers.
- **Unreconciled:** Israel Amendment-13 max fine ceiling (per-capita NIS vs a
  reported "5% of turnover").
- **Evidence gaps (primary research):** B2C willingness-to-pay for a move-out
  report; quantified Israeli deposit-dispute frequency; depth of Paraspot's actual
  reasoning (Inman review blocked, 403); your own wear-vs-damage eval-set accuracy
  on Opus 4.8 before trusting any classification threshold.

---

## What this changes in the app we already built

The DepositShield scaffold (`apps/depositshield/`) already does guided-ish capture,
cautious framing, S3 expiry, and an inspection report. Three changes align it with
the research:

1. **`lib/inspection/schema.ts`** — drop `draft_responsibility` (party verdict);
   replace with neutral factors (`apportionment_note`, "an adjudicator decides").
   Keep `wear_classification` (it's the legally-meaningful, defensible axis).
2. **`lib/inspection/prompt.ts`** — instruct: describe defects + factors, never
   name a responsible party or a cost; keep the cautious disclaimer.
3. **MVP+:** add a server-side capture timestamp and a human-confirm step; S3
   Object Lock + SHA-256 as the evidence-credibility story (optional for the demo).
