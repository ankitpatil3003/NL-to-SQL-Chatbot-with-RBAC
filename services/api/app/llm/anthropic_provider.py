"""Anthropic Messages API provider (official SDK). Optional: used only when an `anthropic:<model>`
entry is in LLM_CHAIN and ANTHROPIC_API_KEY is set."""

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
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (
        usage.input_tokens * price_in
        + usage.cache_read_tokens * price_in * 0.1
        + usage.cache_write_tokens * price_in * 1.25
        + usage.output_tokens * price_out
    ) / 1_000_000


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, *, timeout_s: float = 60.0, client: Any = None) -> None:
        # Retries are the router's job (uniform policy + fallback across providers), so the SDK's
        # own retry loop is off.
        self._client = client or anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout_s, max_retries=0
        )

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
            kwargs["output_config"] = {
                "format": {"type": "json_schema", "schema": strict_json_schema(request.output)}
            }

        started = time.perf_counter()
        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise LLMError(
                f"anthropic rate limited: {exc.message}", retryable=True, status=429
            ) from exc
        except anthropic.APIStatusError as exc:  # after the more specific classes above
            raise LLMError(
                f"anthropic HTTP {exc.status_code}: {exc.message}",
                retryable=exc.status_code >= 500 or exc.status_code in {408, 409},
                status=exc.status_code,
            ) from exc
        except anthropic.APIConnectionError as exc:  # includes APITimeoutError
            raise LLMError(f"anthropic connection error: {exc}", retryable=True) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.stop_reason == "refusal":
            raise LLMError("anthropic refused the request", retryable=False)
        text = "".join(b.text for b in response.content if b.type == "text")
        if not text:
            raise LLMError("anthropic returned no text", retryable=True)

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
