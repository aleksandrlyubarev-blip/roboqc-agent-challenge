from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from roboqc_agent.agents.fmea_risk import FMEAObservation
from roboqc_agent.agents.vision_inspector import DefectObservation
from roboqc_agent.graph import RoboQCPipeline
from roboqc_agent.providers.demo import DemoProvider
from roboqc_agent.providers.vertex_gemini import GenerationResult
from roboqc_agent.schemas import ActionKind, BBox, DefectClass, Severity, Tile


def _tile() -> Tile:
    return Tile(
        board_id="board-1",
        lot_id="lot-1",
        position={"row": 1, "col": 2},  # type: ignore[arg-type]
        magnification=10,
        image_uri="gs://demo/tile.png",
        captured_at=datetime.now(UTC),
        operator_id="op-1",
    )


class _FakeProvider:
    def generate_multimodal(
        self,
        images: Sequence[str | Path],
        prompt: str,
        *,
        response_schema: Any | None = None,
    ) -> GenerationResult:
        obs = [
            DefectObservation(
                defect_class=DefectClass.SHORT_CIRCUIT,
                bbox=BBox(x=10, y=10, w=8, h=8),
                confidence=0.97,
                source="labeled_detector",
            )
        ]
        return GenerationResult(text=None, parsed=obs, raw=None)

    def generate_text(
        self,
        prompt: str,
        *,
        response_schema: Any | None = None,
    ) -> GenerationResult:
        obs = [
            FMEAObservation(
                severity=Severity.CRITICAL,
                default_action=ActionKind.HOLD,
                justification="short circuits the net",
            )
        ]
        return GenerationResult(text=None, parsed=obs, raw=None)


class _TextOnlyProvider(_FakeProvider):
    """Provider that returns raw JSON text instead of parsed objects."""

    def generate_multimodal(
        self,
        images: Sequence[str | Path],
        prompt: str,
        *,
        response_schema: Any | None = None,
    ) -> GenerationResult:
        payload = json.dumps(
            [
                {
                    "defect_class": "short_circuit",
                    "bbox": {"x": 10, "y": 10, "w": 8, "h": 8},
                    "confidence": 0.97,
                    "source": "labeled_detector",
                }
            ]
        )
        return GenerationResult(text=payload, parsed=None, raw=None)


def test_pipeline_runs_full_tile_flow_with_fake_provider() -> None:
    pipeline = RoboQCPipeline(_FakeProvider())
    report = pipeline.inspect_tile(_tile(), "tile.png")

    assert len(report.defects) == 1
    assert len(report.fmea_entries) == 1
    assert report.agent_action.kind is ActionKind.HOLD
    assert report.fmea_entries[0].defect_id == report.defects[0].defect_id


def test_pipeline_parses_raw_json_text_fallback() -> None:
    pipeline = RoboQCPipeline(_TextOnlyProvider())
    report = pipeline.inspect_tile(_tile(), "tile.png")

    assert len(report.defects) == 1
    assert report.defects[0].defect_class is DefectClass.SHORT_CIRCUIT


def test_pipeline_clean_tile_skips_fmea() -> None:
    class _CleanProvider(_FakeProvider):
        def generate_multimodal(
            self,
            images: Sequence[str | Path],
            prompt: str,
            *,
            response_schema: Any | None = None,
        ) -> GenerationResult:
            return GenerationResult(text=None, parsed=[], raw=None)

    pipeline = RoboQCPipeline(_CleanProvider())
    report = pipeline.inspect_tile(_tile(), "tile.png")

    assert report.defects == []
    assert report.fmea_entries == []
    assert report.agent_action.kind is ActionKind.PASS


def test_demo_provider_drives_pipeline_offline() -> None:
    pipeline = RoboQCPipeline(DemoProvider())
    report = pipeline.inspect_tile(_tile(), "fixtures/board-1_r1_c2.png")

    # Demo output is deterministic and internally consistent.
    assert len(report.fmea_entries) == len(report.defects)
    for entry in report.fmea_entries:
        assert entry.defect_id in {defect.defect_id for defect in report.defects}
