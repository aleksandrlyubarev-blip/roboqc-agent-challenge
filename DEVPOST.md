# RoboQC Agent — Devpost submission draft

> Google for Startups AI Agents Challenge · Track 2 (Optimize) ·
> Stack: Agent Development Kit (ADK) + Vertex AI Gemini 2.5 Pro + Pydantic +
> Cloud Run.

*Draft for review — text only, no traction claimed (pre-seed R&D prototype).*

---

## Tagline

**We don't just find defects. We make the real defect rate visible — without
growing your QC headcount.**

## Inspiration

Most "AI for quality control" pitches promise that a model finds defects better
than a person. We started from a different, more honest observation made on the
floor of a high-mix, low-volume electronics shop: the bottleneck is not human
eyesight — it's the **failure modes of the QC *process*** when there is no QC
department.

When a shop builds one or two units of a board per day, there is no inspection
team. A technician and an engineer own quality between other tasks. In that
reality:

- accuracy drifts with fatigue — more escapes at end of shift, before and after
  breaks;
- inspection under a microscope, tile by tile, is slow;
- it is *faster to fix a defect than to document it*, so defects get silently
  reworked and the process feedback is lost;
- with nothing recorded, there is no defect statistics and no root-cause signal;
- there is no photographic audit trail — a compliance blocker for
  defense / aerospace / medical work;
- contamination and real defects get conflated.

The result is **the Hidden Defect Rate Problem**: management sees "1 defect in
1,000" when the real number is an order of magnitude higher, because the honest
data was never captured. The only classic alternatives are to accept the
blindness or to hire a QC team *plus* a documentation team — economically absurd
at this volume. Classic AOI does not help either: programming an
automated-optical-inspection machine per board costs more than the board.

## What it does

**RoboQC Agent** is an ADK-native multi-agent system for first-article SMT
(surface-mount) PCB inspection under a microscope. A technician captures a board
tile by tile; a brigade of specialized agents inspects each tile, classifies
defects, maps them to FMEA severity, decides the next action, and writes an
audit-grade evidence record — keeping the operator in the loop the whole way.

It breaks the dilemma above: **documentation becomes free**. Every tile — clean
or not — produces an evidence record, so the real defect rate becomes visible
for the first time, with no extra headcount.

## How it works — agentic architecture

Four agents, one job each, communicating only through Pydantic contracts
(`schemas.py`). The four-agent decomposition is frozen for the submission
(`docs/non_negotiables.md`).

```
Tile image
   │
   ▼
1. Vision Inspector  (Gemini 2.5 Pro, multimodal)  → defect candidates
   │      class · bbox · confidence · source (labeled vs anomaly)
   ▼
2. FMEA Risk         (Gemini 2.5 Pro, text)         → severity · action · why
   │      mapped against a frozen 10-class FMEA taxonomy
   ▼
3. Supervisor        (deterministic policy core)    → pass / rework / hold /
   │      aggregates per-defect friction-policy decisions   human_review
   ▼
4. Evidence Report   (code + optional Gemini summary)→ immutable audit record
          tile → board (QCReport) → lot (LotSummary)
```

Design choices that matter to judges:

- **Structured output everywhere.** Each agent emits a typed Pydantic object via
  Gemini `response_schema`. Identities (`tile_id`, `defect_id`) are provenance
  the system assigns, not content the model guesses.
- **Determinism where determinism is correct.** The Supervisor's action is a
  rule-based aggregation of a transparent friction-policy engine; only
  perception (Vision, FMEA reasoning) uses the LLM. This is cheaper, faster, and
  auditable.
- **Human-in-the-loop as a first-class gate.** Any low-confidence defect, or any
  always-escalate class (e.g. tombstoning, which signals a lot-wide process
  fault), routes the tile to a human and is logged.
- **Audit trail by default.** Clean tiles are recorded too — that is the whole
  point of making the hidden defect rate visible.
- **Production-shaped, not a slick chat UI.** Telemetry on every Gemini call
  (latency, error, token counts), Cloud Run deploy scaffold, Cloud Logging /
  monitoring policies, and CI (ruff + black + mypy --strict + pytest).

## How we built it

- **ADK** for agent definitions and orchestration.
- **Vertex AI Gemini 2.5 Pro** (us-central1) as the multimodal + text provider,
  behind one provider module with structured output and telemetry hooks.
- **Pydantic v2** for every inter-agent contract.
- **Streamlit** single operator UI; **Cloud Run** deploy; **Python 3.11**.
- An offline `DemoProvider` makes the full pipeline runnable and the test suite
  green with **no Google Cloud credentials**, so the demo always runs.

## Data — public datasets only

Training and demo use only public, commercially-licensed PCB datasets — no
proprietary or customer imagery:

- **DeepPCB** — primary, 6 defect classes (open, short, mousebite, spur, copper,
  pinhole).
- **PKU-Market-PCB** — supplementary, generalization check.
- **VisA (Amazon), PCB1–PCB4** — Apache 2.0, for the anomaly-detection branch.

See `scripts/download_datasets.sh` and `data/CITATIONS.md`. The defect taxonomy
is 10 classes (6 labeled + 4 anomaly: tombstoning, solder bridge, insufficient
solder, missing component), three severities, with a pass/rework/hold/human-review
action mapping.

## Beachhead market

High-mix, low-volume manufacturing — prototypes, custom runs, small
defense / aerospace / medical batches — where no QC department exists and classic
AOI is uneconomical. There, RoboQC Agent has no direct competitor: it *creates* a
QC function where none existed, at the cost of a subscription, with no per-board
programming (the advantage of a vision-language model over classic AOI). Market
expansion toward pre-production lines at larger EMS providers is on the roadmap.

## Roadmap

The software shipped here is the core. The hardware around it is roadmap:

- **RoboQC inspection robot** — automated tile capture (concept stage).
- **Checker** — handheld scanner for manual capture.
- **Neuron Vision Display** — the operator software surface, evolving from this
  Streamlit demo.
- Conformal-calibration HITL to refine confidence thresholds; durable evidence
  backend; real microscope-SDK capture; cross-session process analytics.

## What's next

Tighten anomaly-class recall on held-out PKU data, add the board/lot finalize
endpoints to the Cloud Run service, and pilot with a high-mix shop to measure
defect-escape rate by hour of shift — the metric that proves the thesis.

## Try it

```bash
pip install -e ".[ui]"
streamlit run ui/streamlit_app.py      # offline demo, no credentials needed
```

See `docs/demo.md` for the full walkthrough and `docs/architecture.md` for the
engineering contract.

---

## 3-minute demo video script

- **0:00–0:25 — The problem.** A shop builds 1–2 units of a board a day, no QC
  team. "It's faster to fix a defect than to write it down" — so nobody writes
  it down. Management thinks quality is fine; the real defect rate is hidden.
- **0:25–0:45 — The idea.** RoboQC Agent makes documentation free. Show the one
  tagline line.
- **0:45–1:50 — Live demo.** Open the Streamlit app. Set up the session. Upload
  three tiles: a clean one (🟢 PASS), an insufficient-solder tile (🟡 REWORK),
  and a low-confidence short-circuit tile (🟠 HUMAN_REVIEW). Expand the **Agent
  breakdown** to show Vision → FMEA → Supervisor → Evidence, and the typed
  evidence JSON. Emphasize: one RoboQC decision per tile, four agents under the
  hood, a human gate on uncertainty.
- **1:50–2:20 — Board rollup.** Switch to the rollup tab: board status HOLD,
  defect histogram, senior escalation on the tombstoning tile. "This board's
  real defect picture — captured automatically, with zero extra documentation
  effort."
- **2:20–2:45 — Architecture & rigor.** One slide: ADK + Gemini 2.5 Pro +
  Pydantic + Cloud Run, structured output, telemetry, CI green, public datasets
  only.
- **2:45–3:00 — Roadmap & close.** One slide with the RoboQC inspection robot
  render. "Today the software makes your hidden defect rate visible. Tomorrow the
  robot captures the tiles too." Tagline again.
