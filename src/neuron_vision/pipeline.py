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
from collections.abc import Callable
from contextvars import copy_context
from typing import TypeVar

from .agents import (
    ChiefInspector,
    ComponentInspector,
    MarkingInspector,
    SolderInspector,
    TriageAgent,
)
from .schemas import ComponentReport, MarkingReport, PipelineResult, SolderReport
from .telemetry import get_tracer

_T = TypeVar("_T")

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
        return asyncio.run(self.run_async(image_bytes, on_stage=on_stage))

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
        loop = asyncio.get_running_loop()

        with get_tracer().start_as_current_span("neuron_vision.pipeline") as span:
            span.set_attribute("pipeline.stage_count", 5)
            span.set_attribute("image.size_bytes", len(image_bytes))

            # ── Stage 1: Triage (must complete before specialists) ───────
            triage = await self._run_in_executor(loop, lambda: self._triage.run(image_bytes))
            if on_stage:
                on_stage("triage")

            # ── Stage 2: Parallel specialist inspection ──────────────────
            context = {"triage": triage}
            solder_fut = self._run_in_executor(loop, lambda: self._solder.run(image_bytes, context))
            components_fut = self._run_in_executor(
                loop, lambda: self._components.run(image_bytes, context)
            )
            markings_fut = self._run_in_executor(
                loop, lambda: self._markings.run(image_bytes, context)
            )

            stage2_results = await asyncio.gather(
                solder_fut,
                components_fut,
                markings_fut,
                return_exceptions=True,
            )

            solder = self._coerce_solder(stage2_results[0])
            components = self._coerce_components(stage2_results[1])
            markings = self._coerce_markings(stage2_results[2])

            if on_stage:
                on_stage("solder")
                on_stage("components")
                on_stage("markings")

            # ── Stage 3: Chief ───────────────────────────────────────────
            verdict = await self._run_in_executor(
                loop, lambda: self._chief.run(triage, solder, components, markings)
            )
            if on_stage:
                on_stage("chief")

            duration = time.perf_counter() - t_start
            span.set_attribute("pipeline.duration_seconds", round(duration, 2))
            span.set_attribute("pipeline.verdict", verdict.status)

        return PipelineResult(
            triage=triage,
            solder=solder,
            components=components,
            markings=markings,
            verdict=verdict,
            duration_seconds=round(duration, 2),
        )

    async def _run_in_executor(
        self,
        loop: asyncio.AbstractEventLoop,
        func: Callable[[], _T],
    ) -> _T:
        context = copy_context()
        return await loop.run_in_executor(None, context.run, func)

    @staticmethod
    def _coerce_solder(result: object) -> SolderReport:
        if isinstance(result, SolderReport):
            return result
        exc = result if isinstance(result, Exception) else RuntimeError(str(result))
        logger.exception("Solder Inspector failed during Stage 2", exc_info=exc)
        return SolderReport(
            defects=[],
            overall_solder_quality="reject",
            inspected_joints_estimate=0,
            confidence=0.0,
            summary=f"Solder Inspector failed; route board to human review. Error: {exc}",
        )

    @staticmethod
    def _coerce_components(result: object) -> ComponentReport:
        if isinstance(result, ComponentReport):
            return result
        exc = result if isinstance(result, Exception) else RuntimeError(str(result))
        logger.exception("Component Inspector failed during Stage 2", exc_info=exc)
        return ComponentReport(
            issues=[],
            missing=[],
            misoriented=[],
            shifted=[],
            overall_placement_quality="reject",
            confidence=0.0,
            summary=f"Component Inspector failed; route board to human review. Error: {exc}",
        )

    @staticmethod
    def _coerce_markings(result: object) -> MarkingReport:
        if isinstance(result, MarkingReport):
            return result
        exc = result if isinstance(result, Exception) else RuntimeError(str(result))
        logger.exception("Marking Inspector failed during Stage 2", exc_info=exc)
        return MarkingReport(
            issues=[],
            unreadable=[],
            missing_marks=[],
            qr_valid=False,
            overall_marking_quality="reject",
            confidence=0.0,
            summary=f"Marking Inspector failed; route board to human review. Error: {exc}",
        )
