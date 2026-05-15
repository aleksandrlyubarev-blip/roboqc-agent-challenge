"""Tool execution helpers designed to sit behind ADK tool usage."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from roboqc_agent.tools.base import AbstractTool, ToolResult, ToolUseContext

MAX_CONCURRENCY = 10


@dataclass(slots=True)
class ToolCall:
    """Normalized tool call payload for RoboQC orchestration."""

    name: str
    input: BaseModel | Mapping[str, Any]
    call_id: str | None = None


@dataclass(slots=True)
class ToolBatch:
    """A serial or concurrent execution batch."""

    is_concurrent: bool
    tool_calls: list[ToolCall]


@dataclass(slots=True)
class ToolExecution:
    """Resolved tool call paired with its result."""

    call: ToolCall
    result: ToolResult[Any]


def partition_tool_calls(
    calls: list[ToolCall],
    tools: dict[str, AbstractTool[Any, Any]],
) -> list[ToolBatch]:
    """Partition safe reads into concurrent batches and everything else serially."""

    batches: list[ToolBatch] = []
    current_concurrent: list[ToolCall] = []

    for call in calls:
        tool = tools.get(call.name)
        can_run_concurrently = False

        if tool is not None:
            try:
                parsed = tool.parse_input(call.input)
            except Exception:
                parsed = None
            if parsed is not None:
                can_run_concurrently = tool.is_concurrency_safe(parsed)

        if can_run_concurrently:
            current_concurrent.append(call)
            continue

        if current_concurrent:
            batches.append(ToolBatch(is_concurrent=True, tool_calls=current_concurrent))
            current_concurrent = []
        batches.append(ToolBatch(is_concurrent=False, tool_calls=[call]))

    if current_concurrent:
        batches.append(ToolBatch(is_concurrent=True, tool_calls=current_concurrent))

    return batches


async def _execute_single(
    call: ToolCall,
    tools: dict[str, AbstractTool[Any, Any]],
    context: ToolUseContext,
) -> ToolExecution:
    tool = tools.get(call.name)
    if tool is None:
        return ToolExecution(
            call=call,
            result=ToolResult(
                error=f"Unknown tool: {call.name}",
                metadata={"tool_name": call.name, "call_id": call.call_id},
            ),
        )

    result = await tool.run(call.input, context)
    result.metadata.setdefault("call_id", call.call_id)
    result.metadata.setdefault("tool_name", call.name)
    return ToolExecution(call=call, result=result)


async def run_tools(
    calls: list[ToolCall],
    tools: dict[str, AbstractTool[Any, Any]],
    context: ToolUseContext,
) -> AsyncIterator[ToolExecution]:
    """Run normalized tool calls behind an ADK-facing adapter layer."""

    for batch in partition_tool_calls(calls, tools):
        if batch.is_concurrent:
            semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

            async def run_one(
                call: ToolCall,
                sem: asyncio.Semaphore = semaphore,
            ) -> ToolExecution:
                async with sem:
                    return await _execute_single(call, tools, context)

            results = await asyncio.gather(*(run_one(call) for call in batch.tool_calls))
            for execution in results:
                yield execution
        else:
            for call in batch.tool_calls:
                yield await _execute_single(call, tools, context)
