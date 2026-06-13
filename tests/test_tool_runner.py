from __future__ import annotations

import asyncio

from pydantic import BaseModel

from roboqc_agent.orchestration.tool_runner import ToolCall, partition_tool_calls, run_tools
from roboqc_agent.tools.base import AbstractTool, ToolResult, ToolUseContext


class ReadInput(BaseModel):
    value: str


class ReadTool(AbstractTool[ReadInput, str]):
    name = "read"

    def input_schema(self) -> type[ReadInput]:
        return ReadInput

    async def call(self, args: ReadInput, context: ToolUseContext) -> ToolResult[str]:
        return ToolResult(output=args.value)

    async def prompt(self) -> str:
        return "Read"

    def is_concurrency_safe(self, args: ReadInput) -> bool:
        return True


class WriteTool(ReadTool):
    name = "write"

    def is_concurrency_safe(self, args: ReadInput) -> bool:
        return False


def test_partition_tool_calls_batches_reads_and_serializes_writes() -> None:
    tools = {"read": ReadTool(), "write": WriteTool()}
    batches = partition_tool_calls(
        [
            ToolCall(name="read", input={"value": "a"}),
            ToolCall(name="read", input={"value": "b"}),
            ToolCall(name="write", input={"value": "c"}),
        ],
        tools,
    )

    assert [batch.is_concurrent for batch in batches] == [True, False]
    assert [len(batch.tool_calls) for batch in batches] == [2, 1]


async def _collect_executions() -> list[object]:
    tools = {"read": ReadTool(), "write": WriteTool()}
    return [
        execution
        async for execution in run_tools(
            [
                ToolCall(name="read", input={"value": "a"}),
                ToolCall(name="write", input={"value": "b"}),
            ],
            tools,
            ToolUseContext(),
        )
    ]


def test_run_tools_preserves_request_order() -> None:
    executions = asyncio.run(_collect_executions())
    assert [execution.result.output for execution in executions] == ["a", "b"]


class HangingTool(ReadTool):
    name = "hang"

    async def call(self, args: ReadInput, context: ToolUseContext) -> ToolResult[str]:
        await asyncio.sleep(3600)
        return ToolResult(output="never")


def test_run_tools_times_out_hung_tool(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ROBOQC_TOOL_TIMEOUT_SECONDS", "0.05")
    tools = {"hang": HangingTool(), "read": ReadTool()}

    async def collect() -> list[object]:
        return [
            execution
            async for execution in run_tools(
                [
                    ToolCall(name="hang", input={"value": "x"}, call_id="c1"),
                    ToolCall(name="read", input={"value": "ok"}),
                ],
                tools,
                ToolUseContext(),
            )
        ]

    executions = asyncio.run(collect())
    assert executions[0].result.error is not None
    assert "timed out" in executions[0].result.error
    assert executions[0].result.metadata["call_id"] == "c1"
    assert executions[1].result.output == "ok"


def test_invalid_tool_timeout_env_falls_back_to_default(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from roboqc_agent.orchestration.tool_runner import (
        DEFAULT_TOOL_TIMEOUT_SECONDS,
        _tool_timeout_seconds,
    )

    monkeypatch.setenv("ROBOQC_TOOL_TIMEOUT_SECONDS", "not-a-number")
    assert _tool_timeout_seconds() == DEFAULT_TOOL_TIMEOUT_SECONDS
