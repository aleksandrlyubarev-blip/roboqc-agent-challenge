# RoboQC Agent — Inspection Target Specification

**Status:** FROZEN for Google for Startups AI Agents Challenge submission (deadline 2026-06-05). No target revisions until 2026-06-06.
**Date frozen:** 2026-05-16
**Version:** 2.0 (SMT pivot)

---

## 1. Use case

**RoboQC Agent is a co-pilot for the human QC technician inspecting first-article SMT (surface-mount technology) PCBs under an optical microscope.**

Target workflow:
1. A small production run (typically 10–200 boards) requires manual inspection before mass production is greenlit.
2. A QC technician scans each board tile-by-tile under a benchtop microscope (typically 5×–40× magnification).
3. For each tile, the operator captures an image and passes it to the agent.
4. The agent analyzes the tile, classifies any defects, maps them to FMEA severity, and recommends an action (pass / rework / escalate / hold lot).
5. Operator reviews the agent's decision, accepts or overrides, and the system writes an audit-grade evidence record.

The agent does **not** replace the operator. It accelerates a senior-level inspection task so that a less-experienced technician can perform it at higher throughput with documented evidence.

## 2. Why this use case

- **Pre-production / first-article inspection** is the manufacturing stage where automated optical inspection (AOI) systems do not work well: lot sizes are too small to amortize AOI line setup and calibration cost.
- The work currently requires **scarce senior-level QC technicians**. Their time is the bottleneck.
- Defects at this stage are catastrophic if missed (entire lot may be scrapped or recalled), so any tool used here must be **evidence-generating and human-in-the-loop**, not autonomous.
- The agent's value proposition is measurable: *tiles per hour throughput*, *operator-agent agreement rate*, *false-negative defect rate*, *evidence completeness*.

## 3. Inspection target

A **synthetic SMT first-article inspection workflow** built from public datasets
used under their published terms. RoboQC Agent is evaluated on this corpus for
the submission. No proprietary data, no NDA-encumbered imagery.

### 3.1 Primary dataset — DeepPCB

- **Source:** Tang, He, Liu, Li (2019), Beihang University.
- **Composition:** 1500 image pairs (template + tested), each pair contains 0–N defects with bounding-box and class annotations.
- **Defect classes (6):** open, short, mousebite, spur, copper, pinhole.
- **Resolution:** 640 × 640 typical, suitable as microscope-tile proxy.
- **Terms:** published for research use only. Cited in submission; not
  redistributed.

DeepPCB images are the closest publicly available proxy for the microscope-tile capture format. Each image effectively *is* one inspection tile.

### 3.2 Supplementary dataset — PKU-Market-PCB

- **Source:** Peking University Open Lab on Human-Robot Interaction.
- **Composition:** 693 images, same 6 defect categories as DeepPCB.
- **Role:** out-of-distribution validation. The agent is trained on DeepPCB style and evaluated against PKU style to demonstrate generalization.
- **Terms:** treat as restricted until the final primary-source license note is
  recorded in `data/CITATIONS.md`; do not redistribute.

### 3.3 Supplementary dataset — VisA (PCB1–PCB4 subset)

- **Source:** Amazon Visual Anomaly dataset (Zou et al., 2022).
- **License:** **CC BY 4.0**.
- **Composition:** four distinct PCB types with pixel-level anomaly masks. Total ~4000 images across PCB1, PCB2, PCB3, PCB4.
- **Role:** anomaly-detection branch (for SMT defects beyond the 6 DeepPCB classes — tombstoning, solder bridge, insufficient solder, missing component). These are detected by Gemini multimodal vision without dedicated training; VisA provides validation data for the anomaly-detection arm of the pipeline.

### 3.4 Total inspection categories

10 defect classes total — 6 from labeled datasets, 4 from anomaly-detection arm — defined in `fmea_taxonomy.md`.

## 4. Tile capture model

A **tile** is the atomic unit of inspection.

```python
class Tile:
    board_id: str         # which board in the lot
    position: (row, col)  # microscope-stage coordinate
    magnification: int    # 5, 10, 20, 40
    image: bytes          # PNG, typically ~512–1024 px on long side
    captured_at: datetime
    operator_id: str
```

A board is decomposed into a fixed tile grid (typical: 20×30 = 600 tiles for a 100 × 150 mm board at 10× magnification). The agent processes each tile independently; the Evidence Report Agent aggregates per-board.

## 5. Customer profile

Three plausible Israeli customer segments, in priority order:

1. **R&D prototype shops** (university labs, hardware startups, accelerators). Smallest deal size, fastest sales cycle, no procurement bureaucracy. Beachhead.
2. **Israeli EMS providers** (contract manufacturers serving Israeli OEMs). Medium deal size, real procurement, but real pain.
3. **Defense / aerospace pre-production lines** (Elbit, Rafael, IAI subcontractors). Largest deal size, slowest cycle, security clearance complexity. Long-term target.

NewTech Industry 4.0 conference (Tel Aviv, 2026-07-01) addresses segments 1 and 2 primarily.

## 6. Compliance & legal posture

- Evaluation corpus is sourced from public datasets and tracked with explicit
  citation / license notes.
- No customer data, no proprietary imagery, no reverse-engineered geometry.
- The methodology is fully reproducible by any reviewer from public sources.
- DeepPCB is used only under its research-only publication terms and is not a
  production training asset.
- VisA is licensed under CC BY 4.0 and requires attribution.
- Production deployments would use customer-supplied data or separately
  licensed datasets rather than assuming the submission corpus is commercially
  deployable as-is.

## 7. Freeze notice

This specification is frozen as of 2026-05-16 for the Google submission.

Any future revisions to inspection scope happen after 2026-06-06.
