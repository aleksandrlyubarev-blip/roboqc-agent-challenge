"""Generic typed tool contract used by RoboQC orchestration."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, ValidationError

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput")


class ToolResult(BaseModel, Generic[TOutput]):
    """Structured output returned from a tool execution."""

    output: TOutput | None = None
    error: str | None = None
    output_to_model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None


class PermissionResult(BaseModel):
    """Outcome of a tool permission check."""

    behavior: str = "allow"  # allow | deny | ask
    reason: str = ""
    updated_input: dict[str, Any] | None = None


class ValidationResult(BaseModel):
    """Outcome of business-level tool input validation."""

    ok: bool = True
    reason: str = ""


@dataclass(slots=True)
class ToolUseContext:
    """Minimal execution context shared across RoboQC tools."""

    request_id: str = ""
    inspection_id: str = ""
    working_directory: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    available_tools: dict[str, Any] = field(default_factory=dict, repr=False)


def truncate_text(text: str, max_chars: int) -> str:
    """Keep long tool outputs bounded while preserving head and tail context."""

    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    omitted = len(text) - max_chars
    return f"{text[:half]}\n\n... [{omitted} chars truncated] ...\n\n{text[-half:]}"


class AbstractTool(ABC, Generic[TInput, TOutput]):
    """Reusable lifecycle contract for typed RoboQC tools."""

    name: str = "abstract_tool"
    max_result_size_chars: int = 100_000

    @abstractmethod
    def input_schema(self) -> type[TInput]:
        """Return the Pydantic model used to validate tool input."""

    @abstractmethod
    async def call(self, args: TInput, context: ToolUseContext) -> ToolResult[TOutput]:
        """Execute the concrete tool behavior."""

    @abstractmethod
    async def prompt(self) -> str:
        """Return the LLM-facing tool description."""

    def parse_input(self, raw_args: TInput | Mapping[str, Any]) -> TInput:
        schema = self.input_schema()
        if isinstance(raw_args, schema):
            return raw_args
        if isinstance(raw_args, BaseModel):
            raw_args = raw_args.model_dump()
        return schema.model_validate(raw_args)

    async def check_permissions(
        self,
        args: TInput,
        context: ToolUseContext,
    ) -> PermissionResult:
        return PermissionResult(behavior="allow")

    async def validate_input(
        self,
        args: TInput,
        context: ToolUseContext,
    ) -> ValidationResult:
        return ValidationResult(ok=True)

    def is_read_only(self, args: TInput) -> bool:
        return False

    def is_concurrency_safe(self, args: TInput) -> bool:
        return False

    def is_destructive(self, args: TInput) -> bool:
        return False

    def to_classifier_input(self, args: TInput) -> str:
        return json.dumps(args.model_dump(), default=str, ensure_ascii=False)

    async def run(
        self,
        raw_args: TInput | Mapping[str, Any],
        context: ToolUseContext,
    ) -> ToolResult[TOutput]:
        """Run parse → permission → validation → execute as one stable lifecycle."""

        try:
            args = self.parse_input(raw_args)
        except ValidationError as exc:
            return ToolResult(
                error=f"Input validation failed: {exc.errors()}",
                metadata={"stage": "input_schema", "tool_name": self.name},
            )

        permission = await self.check_permissions(args, context)
        if permission.updated_input:
            try:
                args = self.parse_input(permission.updated_input)
            except ValidationError as exc:
                return ToolResult(
                    error=f"Permission hook returned invalid input: {exc.errors()}",
                    metadata={"stage": "check_permissions", "tool_name": self.name},
                )

        if permission.behavior == "deny":
            return ToolResult(
                error=permission.reason or "Permission denied",
                metadata={"stage": "check_permissions", "tool_name": self.name},
            )

        if permission.behavior == "ask":
            return ToolResult(
                error=permission.reason or "Permission escalation required",
                metadata={
                    "stage": "check_permissions",
                    "tool_name": self.name,
                    "permission_behavior": "ask",
                },
            )

        validation = await self.validate_input(args, context)
        if not validation.ok:
            return ToolResult(
                error=validation.reason or "Business validation failed",
                metadata={"stage": "validate_input", "tool_name": self.name},
            )

        result = await self.call(args, context)
        result.metadata.setdefault("tool_name", self.name)
        result.output_to_model = self._prepare_output_to_model(result)
        return result

    def _prepare_output_to_model(self, result: ToolResult[TOutput]) -> str | None:
        if result.output_to_model is None:
            if result.output is None:
                return None
            try:
                result.output_to_model = json.dumps(
                    result.output,
                    default=str,
                    ensure_ascii=False,
                )
            except TypeError:
                result.output_to_model = str(result.output)

        if result.output_to_model is None:
            return None
        return truncate_text(result.output_to_model, self.max_result_size_chars)
