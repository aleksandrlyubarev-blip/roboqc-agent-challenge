from __future__ import annotations

from pydantic import BaseModel

from roboqc_agent.tools.base import AbstractTool, ToolResult, ToolUseContext


class EchoInput(BaseModel):
    text: str


class EchoTool(AbstractTool[EchoInput, dict[str, str]]):
    name = "echo"

    def input_schema(self) -> type[EchoInput]:
        return EchoInput

    async def call(
        self,
        args: EchoInput,
        context: ToolUseContext,
    ) -> ToolResult[dict[str, str]]:
        return ToolResult(output={"echo": args.text})

    async def prompt(self) -> str:
        return "Echo text"


async def test_tool_lifecycle_returns_structured_output() -> None:
    result = await EchoTool().run({"text": "ok"}, ToolUseContext(request_id="req-1"))

    assert result.success is True
    assert result.output == {"echo": "ok"}
    assert result.metadata["tool_name"] == "echo"


async def test_tool_lifecycle_reports_schema_errors() -> None:
    result = await EchoTool().run({}, ToolUseContext())

    assert result.success is False
    assert result.metadata["stage"] == "input_schema"
