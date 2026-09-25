"""Anthropic Messages API provider (official SDK), serving two chain prefixes:

- `anthropic:<model>`: the first-party API (ANTHROPIC_API_KEY).
- `bedrock:<model>`: Claude in Amazon Bedrock (`AsyncAnthropicBedrockMantle`, same Messages API,
  SigV4-signed with the ECS task role, billed to the AWS account). Bedrock doesn't support
  `output_config` structured outputs, so JSON comes from a forced tool call instead."""

import json
import time
from typing import Any

import anthropic

from app.llm.base import LLMError, LLMRequest, LLMResponse, Usage, strict_json_schema

# USD per million tokens (input, output), first-party API rates. Cache reads bill at ~0.1x input
# and 5-minute cache writes at ~1.25x input.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def _cost(model: str, usage: Usage) -> float | None:
    # Bedrock IDs carry an `anthropic.` prefix; its global endpoint bills at first-party rates.
    price = PRICES.get(model.removeprefix("anthropic."))
    if price is None:
        return None
    price_in, price_out = price
    return (
        usage.input_tokens * price_in
        + usage.cache_read_tokens * price_in * 0.1
        + usage.cache_write_tokens * price_in * 1.25
        + usage.output_tokens * price_out
    ) / 1_000_000


_TOOL = "emit_result"


class AnthropicProvider:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout_s: float = 60.0,
        client: Any = None,
        name: str = "anthropic",
        json_via_tool: bool = False,
    ) -> None:
        # Retries are the router's job (uniform policy + fallback across providers), so the SDK's
        # own retry loop is off.
        self._client = client or anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout_s, max_retries=0
        )
        self.name = name
        self._json_via_tool = json_via_tool

    @classmethod
    def bedrock(cls, region: str, *, timeout_s: float = 60.0) -> "AnthropicProvider":
        """Claude in Amazon Bedrock; credentials from the standard AWS chain (ECS task role)."""
        client = anthropic.AsyncAnthropicBedrockMantle(
            aws_region=region, timeout=timeout_s, max_retries=0
        )
        return cls(client=client, name="bedrock", json_via_tool=True)

    async def complete(self, model: str, request: LLMRequest) -> LLMResponse:
        system: list[dict[str, Any]] = []
        for block in request.system:
            entry: dict[str, Any] = {"type": "text", "text": block.text}
            if block.cache:
                entry["cache_control"] = {"type": "ephemeral"}
            system.append(entry)

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens,
            "system": system,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        if request.output is not None:
            schema = strict_json_schema(request.output)
            if self._json_via_tool:
                kwargs["tools"] = [{"name": _TOOL, "description": "Return the result.",
                                    "input_schema": schema}]  # fmt: skip
                kwargs["tool_choice"] = {"type": "tool", "name": _TOOL}
            else:
                kwargs["output_config"] = {"format": {"type": "json_schema", "schema": schema}}

        started = time.perf_counter()
        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise LLMError(
                f"{self.name} rate limited: {exc.message}", retryable=True, status=429
            ) from exc
        except anthropic.APIStatusError as exc:  # after the more specific classes above
            raise LLMError(
                f"{self.name} HTTP {exc.status_code}: {exc.message}",
                retryable=exc.status_code >= 500 or exc.status_code in {408, 409},
                status=exc.status_code,
            ) from exc
        except anthropic.APIConnectionError as exc:  # includes APITimeoutError
            raise LLMError(f"{self.name} connection error: {exc}", retryable=True) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.stop_reason == "refusal":
            raise LLMError(f"{self.name} refused the request", retryable=False)
        tool_inputs = [b.input for b in response.content if b.type == "tool_use"]
        if tool_inputs:
            text = json.dumps(tool_inputs[0])
        else:
            text = "".join(b.text for b in response.content if b.type == "text")
        if not text:
            raise LLMError(f"{self.name} returned no text", retryable=True)

        u = response.usage
        usage = Usage(
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_read_tokens=u.cache_read_input_tokens or 0,
            cache_write_tokens=u.cache_creation_input_tokens or 0,
        )
        usage.cost_usd = _cost(model, usage)
        return LLMResponse(
            text=text, usage=usage, provider=self.name, model=model, latency_ms=latency_ms
        )

    async def aclose(self) -> None:
        await self._client.close()
