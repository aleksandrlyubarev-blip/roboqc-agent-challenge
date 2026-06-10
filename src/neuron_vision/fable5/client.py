"""
Production client for Claude Fable 5 (Anthropic Messages API).

Design notes
------------
* **Model surface.** ``claude-fable-5`` accepts adaptive thinking only:
  ``thinking={"type": "adaptive"}``. Sampling params (``temperature`` /
  ``top_p`` / ``top_k``) and ``budget_tokens`` are rejected with 400, so they
  are never sent. An explicit ``thinking: {"type": "disabled"}`` is also a 400
  on Fable 5 — omit the field instead.
* **Structured output.** We use ``output_config.format`` with a JSON schema
  derived from our Pydantic models. The API rejects numeric range
  constraints, so :func:`sanitize_json_schema` strips them from the wire
  schema; Pydantic re-validates the full constraints client-side.
* **Fallback.** Fable 5 has guardrails and may refuse sensitive topics
  (``stop_reason == "refusal"``); it is also the most contended tier. On
  refusal, rate-limit exhaustion, overload, server error or timeout we retry
  once on Claude Opus 4.8 (cheaper, same API surface) and tag the response so
  the caller can see degraded provenance.
* **Retries.** The Anthropic SDK already retries 429/5xx with exponential
  backoff (``max_retries``); we do not duplicate that loop — we only add the
  cross-model fallback on final failure.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar

import anthropic
from anthropic.types import OutputConfigParam, TextBlockParam
from pydantic import BaseModel, ValidationError

from neuron_vision.fable5.cache import TTLCache
from neuron_vision.fable5.schemas import (
    DefectAnalysisRequest,
    DefectReasoning,
    DefectReasoningResponse,
    Fable5CallMeta,
    RecommendationSet,
    RecommendationsResponse,
    RootCauseAnalysis,
    RootCauseResponse,
)
from neuron_vision.fable5.telemetry import (
    Fable5CallEvent,
    estimate_cost_usd,
    log_fable5_event,
)

TModel = TypeVar("TModel", bound=BaseModel)

# Keys the structured-outputs API does not support; enforced client-side instead.
_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
    }
)

# Kept stable and byte-identical across requests so the prompt-caching prefix
# (tools -> system -> messages) stays reusable. Do not interpolate timestamps,
# request IDs or any per-request data into this string.
SYSTEM_PROMPT = """\
You are the senior reasoning engine of Neuron Vision Display (RomeoFlexVision), an AI quality
assistant for display-panel manufacturing. Vision-inspection agents hand you structured defect
observations; your job is deep causal analysis for QC engineers.

Operating rules:
1. Reason from manufacturing physics: panel processes (TFT array, cell assembly, module/bonding,
   final QC), materials, equipment and environment. Connect each observed defect to a plausible
   physical mechanism before naming a cause.
2. Distinguish the single most likely root cause from contributing factors. Explicitly list
   hypotheses you ruled out and why — engineers must see the reasoning, not just the verdict.
3. Calibrate confidence honestly. If the evidence is thin, say so and recommend the cheapest
   discriminating check first.
4. Recommendations must be concrete and actionable on a production line: name the process stage,
   the parameter or component to check, and the expected effect on the defect rate.
5. Respond strictly in the JSON schema enforced for this request. No prose outside the schema.
"""


class Fable5Error(RuntimeError):
    """Raised when both the primary and fallback model calls fail."""


@dataclass(slots=True)
class Fable5Config:
    """Tunables for the Fable 5 client."""

    primary_model: str = "claude-fable-5"
    fallback_model: str = "claude-opus-4-8"
    max_tokens: int = 16_000
    # Complex causal analysis needs headroom; the SDK default (10 min) is too
    # lax for an interactive dashboard, 120 s matches our UX budget.
    timeout_seconds: float = 120.0
    sdk_max_retries: int = 3
    cache_ttl_seconds: float = 300.0
    cache_max_entries: int = 256
    effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    extra_client_kwargs: dict[str, Any] = field(default_factory=dict)


def sanitize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Make a Pydantic-generated JSON schema acceptable to structured outputs.

    Removes unsupported constraint keywords and forces
    ``additionalProperties: false`` on every object node (required by the API).
    """

    cleaned = copy.deepcopy(schema)

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in list(node):
                if key in _UNSUPPORTED_SCHEMA_KEYS:
                    del node[key]
            if node.get("type") == "object":
                node["additionalProperties"] = False
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(cleaned)
    return cleaned


def _extract_text(content: list[Any]) -> str:
    """Return the first text block of a Messages API response."""

    for block in content:
        if getattr(block, "type", None) == "text":
            text: str = block.text
            return text
    raise Fable5Error("Model response contained no text block")


class Fable5Client:
    """
    Async client exposing the three reasoning operations used by the product:

    * :meth:`reason` — full analysis (summary + root cause + recommendations)
    * :meth:`analyze_root_cause` — causal analysis only
    * :meth:`generate_recommendations` — recommendations only
    """

    def __init__(
        self,
        api_key: str,
        config: Fable5Config | None = None,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self._config = config or Fable5Config()
        self._client = client or anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=self._config.timeout_seconds,
            max_retries=self._config.sdk_max_retries,
            **self._config.extra_client_kwargs,
        )
        self._cache = TTLCache(
            max_entries=self._config.cache_max_entries,
            ttl_seconds=self._config.cache_ttl_seconds,
        )

    # -- public operations --------------------------------------------------

    async def reason(self, request: DefectAnalysisRequest) -> DefectReasoningResponse:
        """Full defect analysis: explanation, root cause and recommendations."""

        result, meta = await self._structured_call(
            operation="reason",
            user_prompt=self._render_request(request, focus="full analysis"),
            output_model=DefectReasoning,
        )
        return DefectReasoningResponse(result=result, meta=meta)

    async def analyze_root_cause(self, request: DefectAnalysisRequest) -> RootCauseResponse:
        """Causal / root-cause analysis for a defect set."""

        result, meta = await self._structured_call(
            operation="analyze_root_cause",
            user_prompt=self._render_request(request, focus="root cause analysis only"),
            output_model=RootCauseAnalysis,
        )
        return RootCauseResponse(result=result, meta=meta)

    async def generate_recommendations(
        self, request: DefectAnalysisRequest
    ) -> RecommendationsResponse:
        """Actionable recommendations for QC / process engineers."""

        result, meta = await self._structured_call(
            operation="generate_recommendations",
            user_prompt=self._render_request(
                request, focus="actionable recommendations for the line"
            ),
            output_model=RecommendationSet,
        )
        return RecommendationsResponse(result=result, meta=meta)

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _render_request(request: DefectAnalysisRequest, focus: str) -> str:
        """Serialize the request as a compact, deterministic user prompt."""

        payload = request.model_dump_json(exclude_none=True)
        return (
            f"Requested output: {focus}.\n"
            f"Defect observations and manufacturing context (JSON):\n{payload}"
        )

    async def _structured_call(
        self,
        operation: str,
        user_prompt: str,
        output_model: type[TModel],
    ) -> tuple[TModel, Fable5CallMeta]:
        """Run one structured call with cache, fallback and telemetry."""

        cache_key = TTLCache.fingerprint(operation, {"prompt": user_prompt})
        cached = self._cache.get(cache_key)
        if cached is not None:
            return (
                output_model.model_validate_json(cached),
                Fable5CallMeta(model_id=self._config.primary_model, cached=True),
            )

        wire_schema = sanitize_json_schema(output_model.model_json_schema())

        try:
            result, meta = await self._call_model(
                model=self._config.primary_model,
                operation=operation,
                user_prompt=user_prompt,
                wire_schema=wire_schema,
                output_model=output_model,
            )
        except _FallbackTrigger as trigger:
            log_fable5_event(
                Fable5CallEvent(
                    event="fable5_fallback",
                    model=self._config.fallback_model,
                    operation=operation,
                    latency_ms=trigger.latency_ms,
                    fallback_from=self._config.primary_model,
                    fallback_reason=trigger.reason,
                    error_type=trigger.error_type,
                )
            )
            try:
                result, meta = await self._call_model(
                    model=self._config.fallback_model,
                    operation=operation,
                    user_prompt=user_prompt,
                    wire_schema=wire_schema,
                    output_model=output_model,
                )
            except _FallbackTrigger as fallback_failure:
                raise Fable5Error(
                    f"Both {self._config.primary_model} and {self._config.fallback_model} "
                    f"failed for operation '{operation}': {fallback_failure.reason}"
                ) from fallback_failure
            meta = meta.model_copy(
                update={"fallback_used": True, "fallback_reason": trigger.reason}
            )

        self._cache.put(cache_key, result.model_dump_json())
        return result, meta

    async def _call_model(
        self,
        model: str,
        operation: str,
        user_prompt: str,
        wire_schema: dict[str, Any],
        output_model: type[TModel],
    ) -> tuple[TModel, Fable5CallMeta]:
        """One model invocation; raises _FallbackTrigger on retryable outcomes."""

        started = time.monotonic()
        system_blocks: list[TextBlockParam] = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                # Prompt-cache the stable prefix; harmless if below the
                # model's minimum cacheable size.
                "cache_control": {"type": "ephemeral"},
            }
        ]
        output_config: OutputConfigParam = {
            "effort": self._config.effort,
            "format": {"type": "json_schema", "schema": wire_schema},
        }
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=self._config.max_tokens,
                # Adaptive is the only thinking mode Fable 5 accepts; it also
                # gives the best causal-reasoning quality per token.
                thinking={"type": "adaptive"},
                output_config=output_config,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except (
            anthropic.RateLimitError,
            anthropic.InternalServerError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
        ) as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            self._log_error(model, operation, latency_ms, type(exc).__name__)
            raise _FallbackTrigger(
                reason=f"transport: {type(exc).__name__}",
                error_type=type(exc).__name__,
                latency_ms=latency_ms,
            ) from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        if response.stop_reason == "refusal":
            # Fable 5 guardrails (e.g. cyber/bio categories) — reroute to Opus 4.8.
            stop_details = getattr(response, "stop_details", None)
            category = getattr(stop_details, "category", None) or "unspecified"
            self._log_error(model, operation, latency_ms, f"refusal:{category}")
            raise _FallbackTrigger(
                reason=f"refusal (category={category})",
                error_type="refusal",
                latency_ms=latency_ms,
            )

        if response.stop_reason == "max_tokens":
            self._log_error(model, operation, latency_ms, "max_tokens_truncated")
            raise Fable5Error(
                f"{model} hit max_tokens={self._config.max_tokens}; output is incomplete. "
                "Raise Fable5Config.max_tokens (and switch to streaming above ~16K)."
            )

        try:
            result = output_model.model_validate_json(_extract_text(list(response.content)))
        except ValidationError as exc:
            # output_config guarantees schema-valid JSON, so this indicates a
            # schema drift between our Pydantic model and the wire schema.
            self._log_error(model, operation, latency_ms, "validation_error")
            raise Fable5Error(f"Schema validation failed for {operation}: {exc}") from exc

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        log_fable5_event(
            Fable5CallEvent(
                event="fable5_call",
                model=model,
                operation=operation,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=cost,
                request_id=getattr(response, "_request_id", None),
            )
        )
        meta = Fable5CallMeta(
            model_id=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
        )
        return result, meta

    @staticmethod
    def _log_error(model: str, operation: str, latency_ms: int, error_type: str) -> None:
        log_fable5_event(
            Fable5CallEvent(
                event="fable5_error",
                model=model,
                operation=operation,
                latency_ms=latency_ms,
                error_type=error_type,
            )
        )

    async def aclose(self) -> None:
        """Release the underlying HTTP client."""

        await self._client.close()


class _FallbackTrigger(Exception):
    """Internal: primary-model outcome that warrants one fallback attempt."""

    def __init__(self, reason: str, error_type: str, latency_ms: int) -> None:
        super().__init__(reason)
        self.reason = reason
        self.error_type = error_type
        self.latency_ms = latency_ms
