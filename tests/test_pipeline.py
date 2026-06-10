"""Integration tests for the neuron_vision pipeline orchestration.

The five agents are replaced with fakes so no Vertex AI access is needed;
the tests exercise the real orchestration code (stage ordering, parallel
Stage 2, failure coercion) and the DemoPipeline twin.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from opentelemetry import trace

from neuron_vision import pipeline as pipeline_module
from neuron_vision.demo_mode import DemoPipeline, _scenario_pass
from neuron_vision.pipeline import NeuronVisionPipeline

_SAMPLE = _scenario_pass()
_IMAGE = b"\xff\xd8\xff fake-jpeg-bytes"


class _FakeAgent:
    def __init__(self, result: Any) -> None:
        self._result = result

    def run(self, *args: Any, **kwargs: Any) -> Any:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


@pytest.fixture()
def fake_agents(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    results: dict[str, Any] = {
        "triage": _SAMPLE.triage,
        "solder": _SAMPLE.solder,
        "components": _SAMPLE.components,
        "markings": _SAMPLE.markings,
        "chief": _SAMPLE.verdict,
    }
    monkeypatch.setattr(
        pipeline_module, "TriageAgent", lambda project_id=None: _FakeAgent(results["triage"])
    )
    monkeypatch.setattr(
        pipeline_module, "SolderInspector", lambda project_id=None: _FakeAgent(results["solder"])
    )
    monkeypatch.setattr(
        pipeline_module,
        "ComponentInspector",
        lambda project_id=None: _FakeAgent(results["components"]),
    )
    monkeypatch.setattr(
        pipeline_module,
        "MarkingInspector",
        lambda project_id=None: _FakeAgent(results["markings"]),
    )
    monkeypatch.setattr(
        pipeline_module, "ChiefInspector", lambda project_id=None: _FakeAgent(results["chief"])
    )
    monkeypatch.setattr(pipeline_module, "get_tracer", lambda: trace.NoOpTracer())
    return results


def test_pipeline_runs_all_stages_in_order(fake_agents: dict[str, Any]) -> None:
    stages: list[str] = []
    result = NeuronVisionPipeline().run(_IMAGE, on_stage=stages.append)

    assert stages == ["triage", "solder", "components", "markings", "chief"]
    assert result.verdict.status == "pass"
    assert result.duration_seconds >= 0


def test_pipeline_coerces_failed_specialist_to_reject(fake_agents: dict[str, Any]) -> None:
    fake_agents["solder"] = RuntimeError("Vertex AI unavailable")

    result = NeuronVisionPipeline().run(_IMAGE)

    assert result.solder.overall_solder_quality == "reject"
    assert result.solder.confidence == 0.0
    assert "human review" in result.solder.summary
    # Other specialists are unaffected by the failure.
    assert result.components.overall_placement_quality == "acceptable"


def test_demo_pipeline_sync_and_async_agree() -> None:
    demo = DemoPipeline(scenario="rework", speed=0.0)
    stages_sync: list[str] = []
    stages_async: list[str] = []

    sync_result = demo.run(_IMAGE, on_stage=stages_sync.append)
    async_result = asyncio.run(demo.run_async(_IMAGE, on_stage=stages_async.append))

    assert stages_sync == stages_async == DemoPipeline.STAGE_ORDER
    assert sync_result.verdict.status == async_result.verdict.status == "rework"


def test_demo_pipeline_scenario_choice_is_deterministic() -> None:
    demo = DemoPipeline(speed=0.0)
    first = demo.run(_IMAGE).verdict.status
    second = demo.run(_IMAGE).verdict.status
    assert first == second
