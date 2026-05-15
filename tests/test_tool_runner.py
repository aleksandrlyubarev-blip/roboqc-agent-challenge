from __future__ import annotations

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


async def test_run_tools_preserves_request_order() -> None:
    tools = {"read": ReadTool(), "write": WriteTool()}
    executions = [
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

    assert [execution.result.output for execution in executions] == ["a", "b"]
