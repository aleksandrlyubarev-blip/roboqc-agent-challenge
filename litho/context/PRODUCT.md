# Neuron Vision — product canon

Human-maintained authority for documentation. Preserve these boundaries; cite code for implementation claims.
If code and intent differ, document the gap instead of inventing implementation.

## Product thesis
We do not build a humanoid body. We put an evidence-backed inspection brain (SOP + visual agents + CAD bridge) onto a purchased mobile/manipulator platform for EMS / SMT incoming QC.

## Container contract
Repository: aleksandrlyubarev-blip/roboqc-agent-challenge
System role: five-agent PCB/SMT visual inspection.
Actor: PCB/SMT quality inspector.
Input: board image bytes from an uploaded photograph or an external camera capture.
Output: structured QCVerdict with pass, rework, hold or human_review and an evidence_log.
The five roles are exactly triage, solder, component, marking and chief.
Implemented: src/neuron_vision/pipeline.py runs triage, then three specialists in parallel, then chief.
Implemented: src/neuron_vision/agents/ holds the five agent implementations.
Implemented: src/neuron_vision/schemas.py defines QCVerdict and PipelineResult.
The existing src/roboqc_agent/graph.py is a separate four-agent ADK skeleton; do not confuse it with Neuron Vision.
The five-role count applies to the Neuron Vision container, not every experiment in this repository.
System fail-closed requirement: absent or conflicting evidence must prevent automatic release and require review.
Do not claim the model-based chief has the same deterministic guarantees as Inspection Copilot policy.py.
A Neuron Vision evidence_log alone is not a system-wide SHA-256 evidence pack.
Not demonstrated: direct production wiring to Romeo, Inspection Copilot, Buxter or a purchased robot.

## System flow
Camera (External) -> FlexVision Checker capture/frame QA -> Romeo task routing -> Neuron Vision observations -> Inspection Copilot SOP/evidence policy -> human review/disposition -> PASS | REWORK | HOLD | HUMAN REVIEW; Buxter optionally proposes validated CAD/rework geometry.
Romeo owns orchestration and HITL; Neuron Vision owns five visual roles; Copilot owns the deterministic SOP gate.
Buxter defaults to FreeCAD, with optional Fusion and explicit validate/printability checks.
This flow is the target integration; the five repositories do not yet prove one connected deployment.
Target: verdict plus SHA-256 evidence pack including provenance and human disposition.

## External boundary
Purchased mobile base + manipulator + camera: External hardware, not our IP.
Flex line, Technion lab and Israel Physical AI testbed: External target environments, not asserted deployments.
Robot platform drivers and the unified hardware integration are not implemented by this documentation scaffold.

## Source snapshot
Initial audit: af276fd2606b7d052f1f7c92dd202fd7e87cf357 (2026-09-17).
Regeneration must cite the checkout being analyzed and distinguish new code from this initial audit.
Only public source code and synthetic examples may enter documentation generation.
