"""
RomeoFlexVision Pipeline — orchestrates the 5-agent QC brigade.

Flow:
    [PCB image]
        │
        ▼
    TriageAgent              ← Stage 1: risk zone mapping
        │
        ├─────────────────────────────────────┐
        ▼                    ▼                ▼
    SolderInspector  ComponentInspector  MarkingInspector   ← Stage 2: parallel specialists
        │                    │                │
        └─────────────────────────────────────┘
                             │
                             ▼
                      ChiefInspector           ← Stage 3: reasoning & verdict
                             │
                             ▼
                        QCVerdict              ← pass / rework / hold / human_review
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable

from .agents import (
    ChiefInspector,
    ComponentInspector,
    MarkingInspector,
    SolderInspector,
    TriageAgent,
)
from .schemas import PipelineResult

logger = logging.getLogger(__name__)


class NeuronVisionPipeline:
    """
    Orchestrates the full 5-agent PCB QC brigade.

    Usage::

        pipeline = NeuronVisionPipeline()
        result = pipeline.run(image_bytes, on_stage=callback)

    ``on_stage`` is an optional callable(stage_name: str) invoked after
    each stage completes — useful for driving progress indicators in the UI.
    """

    def __init__(self) -> None:
        self._triage = TriageAgent()
        self._solder = SolderInspector()
        self._components = ComponentInspector()
        self._markings = MarkingInspector()
        self._chief = ChiefInspector()

    def run(
        self,
        image_bytes: bytes,
        on_stage: Callable[[str], None] | None = None,
    ) -> PipelineResult:
        """
        Run the complete QC pipeline synchronously.

        Args:
            image_bytes: Raw image bytes (JPEG or PNG).
            on_stage:    Optional progress callback.  Called with stage names:
                         "triage", "solder", "components", "markings", "chief".

        Returns:
            PipelineResult with all agent outputs and the final QC verdict.
        """
        t_start = time.perf_counter()

        # ── Stage 1: Triage ─────────────────────────────────────────────
        logger.info("Pipeline: Stage 1 — Triage Agent")
        triage = self._triage.run(image_bytes)
        if on_stage:
            on_stage("triage")

        # ── Stage 2: Parallel specialist inspection ──────────────────────
        logger.info("Pipeline: Stage 2 — Parallel specialist inspection")
        context = {"triage": triage}

        solder = self._solder.run(image_bytes, context=context)
        if on_stage:
            on_stage("solder")

        components = self._components.run(image_bytes, context=context)
        if on_stage:
            on_stage("components")

        markings = self._markings.run(image_bytes, context=context)
        if on_stage:
            on_stage("markings")

        # ── Stage 3: Chief Inspector ─────────────────────────────────────
        logger.info("Pipeline: Stage 3 — Chief Inspector (reasoning)")
        verdict = self._chief.run(triage, solder, components, markings)
        if on_stage:
            on_stage("chief")

        duration = time.perf_counter() - t_start
        logger.info("Pipeline: complete in %.2fs — verdict: %s", duration, verdict.status)

        return PipelineResult(
            triage=triage,
            solder=solder,
            components=components,
            markings=markings,
            verdict=verdict,
            duration_seconds=round(duration, 2),
        )

    async def run_async(
        self,
        image_bytes: bytes,
        on_stage: Callable[[str], None] | None = None,
    ) -> PipelineResult:
        """
        Async version: runs Stage 2 specialist agents concurrently.

        Provides ~2-3× speedup over sequential execution for Stage 2.
        """
        t_start = time.perf_counter()

        # ── Stage 1: Triage (must complete before specialists) ───────────
        triage = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._triage.run(image_bytes)
        )
        if on_stage:
            on_stage("triage")

        # ── Stage 2: Parallel ────────────────────────────────────────────
        context = {"triage": triage}

        loop = asyncio.get_event_loop()
        solder_fut = loop.run_in_executor(None, lambda: self._solder.run(image_bytes, context))
        components_fut = loop.run_in_executor(None, lambda: self._components.run(image_bytes, context))
        markings_fut = loop.run_in_executor(None, lambda: self._markings.run(image_bytes, context))

        solder, components, markings = await asyncio.gather(
            solder_fut, components_fut, markings_fut
        )
        if on_stage:
            on_stage("solder")
            on_stage("components")
            on_stage("markings")

        # ── Stage 3: Chief ───────────────────────────────────────────────
        verdict = await loop.run_in_executor(
            None, lambda: self._chief.run(triage, solder, components, markings)
        )
        if on_stage:
            on_stage("chief")

        duration = time.perf_counter() - t_start
        return PipelineResult(
            triage=triage,
            solder=solder,
            components=components,
            markings=markings,
            verdict=verdict,
            duration_seconds=round(duration, 2),
        )
