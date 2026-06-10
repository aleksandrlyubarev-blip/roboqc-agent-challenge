# Neuron Vision — V5 voice-over script

**Replaces:** TASK 1 in `V4_HACKATHON_DELIVERABLES.md`
**Runtime:** 175 s video · ~380 words ≈ 150 s of speech (natural pauses included)
**Tone:** engineer-to-engineer. No filler, no "imagine a world".
**Delivery:** read at a normal conversational pace; the timecodes below match
the final cut of `neuron_vision_V5_fable.mp4` (8 segments, crossfades at the
boundaries).
**Synthesized track:** `make_voiceover.py` renders this script with Piper TTS
(`en_US-ryan-high`) — the shipped mp4 already carries that narration. The
text below is the human-readable master; the TTS copy in `make_voiceover.py`
spells out numerals and abbreviations for clean pronunciation.

---

## [0:00 – 0:18] · v5_01_cost_stat — HOOK

> An automated optical inspection machine costs half a million to a million
> dollars. That's the entry ticket for catching solder defects on a PCB line.
> Most small electronics shops never pay it — they inspect by eye, and
> defects ship.

## [0:18 – 0:49] · v5_02_pipeline — ARCHITECTURE

> Neuron Vision replaces that machine with five Gemini agents. A photo of the
> board hits the Triage agent, which decides what deserves a closer look.
> Then three specialists fan out in parallel — solder joints, component
> placement, silkscreen markings. A Chief Inspector reads all three reports
> and issues the verdict: pass, or reject with the defect named and located.
> Every agent returns structured JSON, enforced by Pydantic v2 response
> schemas. No parsing. No prompt glue.

## [0:49 – 1:10] · v5_03_demo — LIVE, NOT A DECK

> This isn't a slide deck. It's deployed on Cloud Run, running Gemini 2.5 Pro
> in us-central1, right now. Upload a board photo; get a named, located
> defect in seconds. The URL is on screen — judges, you're welcome to try to
> break it.

## [1:10 – 1:32] · v5_04_speed_compare — SPEED

> The three specialists don't queue. One asyncio-gather call runs them
> concurrently. Sequential inspection took fourteen point one seconds;
> parallel takes four point seven. Same model, same prompts — three times
> faster, because the bottleneck was the architecture, not the model.

## [1:32 – 1:55] · v5_05_impact — ROI

> Do the math. An AOI machine is up to a million dollars of capex and weeks
> of reprogramming for every new board design. Neuron Vision is zero
> infrastructure, cents per inspection, and a new design means editing a
> prompt. This is QC that scales down to a ten-person shop — not just up to
> a gigafactory.

## [1:55 – 2:16] · v5_06_observability — ARIZE PHOENIX

> And it's not a black box. Every run is traced with Arize Phoenix:
> one hundred forty-two traces so far, ninety-eight point six percent
> success, P95 latency six point two seconds. When an agent disagrees with a
> human inspector, we replay exactly what it saw — and what it said.

## [2:16 – 2:39] · v5_07_tech_code — THE CODE

> The whole pipeline is this honest. Typed agents, one gather call, and
> response schemas generated straight from Pydantic models. No frameworks
> fighting frameworks — Vertex AI and about two hundred lines of
> orchestration you can actually read.

## [2:39 – 2:55] · v5_08_cta — CLOSE

> Neuron Vision. Factory-grade inspection, no factory budget required. The
> demo is live, the repo is open — links on screen. Built for the Google
> Cloud Rapid Agent Hackathon, traced end to end with Arize Phoenix.

---

### Fact check (against this repo)

| Claim | Source |
|---|---|
| 5 agents: Triage → [Solder, Component, Marking] → Chief | `src/neuron_vision/agents/*.py` |
| `asyncio.gather()` stage-2 parallelism | `src/neuron_vision/pipeline.py:115` |
| 14.1 s → 4.7 s (3×) | V4 benchmark, sequential vs parallel run |
| Pydantic v2 → `response_schema` | `src/neuron_vision/agents/base.py` |
| Gemini 2.5 Pro, us-central1 | `src/neuron_vision/agents/base.py:24` |
| Phoenix: 142 traces · 98.6% · P95 6.2 s | Arize Phoenix project dashboard |
| ~200-line orchestrator | `pipeline.py` = 203 lines |
| Live URL | `https://neuron-vision-display-z3mwyxcila-uc.a.run.app` |
