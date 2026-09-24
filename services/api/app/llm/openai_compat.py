"""Provider for OpenAI-compatible chat-completions APIs: OpenRouter, Cerebras, Groq, Gemini's
compatibility endpoint, a local vLLM/Ollama, ... One adapter, many vendors.

Plain httpx, no vendor SDK: the wire format is small and stable, and keeping it explicit makes
the per-vendor quirks (OpenRouter's cost reporting, reasoning fields) visible here.
"""

import time
from typing import Any

import httpx

from app.llm.base import LLMError, LLMRequest, LLMResponse, Usage, strict_json_schema

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


class OpenAICompatProvider:
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        *,
        timeout_s: float = 60.0,
        extra_headers: dict[str, str] | None = None,
        extra_body: dict[str, Any] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,  # tests inject a MockTransport
    ) -> None:
        self.name = name
        self._extra_body = extra_body or {}
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}", **(extra_headers or {})},
            timeout=timeout_s,
            transport=transport,
        )

    async def complete(self, model: str, request: LLMRequest) -> LLMResponse:
        system = "\n\n".join(block.text for block in request.system)
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                *([{"role": "system", "content": system}] if system else []),
                *({"role": m.role, "content": m.content} for m in request.messages),
            ],
            "max_tokens": request.max_tokens,
            **self._extra_body,
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.output is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.output.__name__,
                    "strict": True,
                    "schema": strict_json_schema(request.output),
                },
            }

        started = time.perf_counter()
        try:
            resp = await self._client.post("/chat/completions", json=body)
        except httpx.TimeoutException as exc:
            raise LLMError(f"{self.name}: timeout", retryable=True) from exc
        except httpx.TransportError as exc:
            raise LLMError(f"{self.name}: connection error: {exc}", retryable=True) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        if resp.status_code >= 400:
            raise LLMError(
                f"{self.name} HTTP {resp.status_code}: {resp.text[:300]}",
                retryable=resp.status_code in RETRYABLE_STATUS,
                status=resp.status_code,
            )
        payload = resp.json()
        # OpenRouter can return HTTP 200 with an error object (e.g. upstream provider failure).
        if error := payload.get("error"):
            code = error.get("code") if isinstance(error, dict) else None
            raise LLMError(
                f"{self.name}: {error}",
                retryable=not isinstance(code, int) or code in RETRYABLE_STATUS,
                status=code if isinstance(code, int) else None,
            )
        choices = payload.get("choices") or []
        text = (choices[0].get("message") or {}).get("content") if choices else None
        if not text:
            # Reasoning models occasionally spend the whole budget thinking and return no answer.
            raise LLMError(f"{self.name}: empty completion", retryable=True)

        usage = payload.get("usage") or {}
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        cost = usage.get("cost")
        return LLMResponse(
            text=text,
            usage=Usage(
                input_tokens=int(usage.get("prompt_tokens") or 0),
                output_tokens=int(usage.get("completion_tokens") or 0),
                cache_read_tokens=int(cached),
                cost_usd=float(cost)
                if cost is not None
                else (0.0 if model.endswith(":free") else None),
            ),
            provider=self.name,
            model=payload.get("model") or model,
            latency_ms=latency_ms,
            raw=payload,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
