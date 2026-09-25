"""Amazon Bedrock Converse API: one adapter for every Bedrock model family (OpenAI gpt-oss, Amazon
Nova, Meta Llama, DeepSeek, Mistral, ...) as `bedrock-converse:<model id or inference profile>`.
Signed with the standard AWS credential chain (the ECS task role) and billed to the AWS account.

Converse has no model-independent JSON mode, so structured output is requested in the system
prompt (the schema, "JSON only"); the router validates it and retries or falls back on bad JSON,
exactly as for the other providers. botocore is synchronous, so calls run in a worker thread.
"""

import asyncio
import json
import time
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, ConnectionError, ReadTimeoutError

from app.llm.base import LLMError, LLMRequest, LLMResponse, Usage, strict_json_schema

# USD per million tokens (input, output), Bedrock on-demand list prices; matched by substring.
PRICES: dict[str, tuple[float, float]] = {
    "gpt-oss-120b": (0.15, 0.60),
    "gpt-oss-20b": (0.07, 0.30),
    "nova-pro": (0.80, 3.20),
    "nova-lite": (0.06, 0.24),
    "llama4-maverick": (0.24, 0.97),
    "deepseek.r1": (1.35, 5.40),
}

RETRYABLE_CODES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "InternalServerException",
    "ModelNotReadyException",
    "ModelTimeoutException",
}

JSON_INSTRUCTION = (
    "Respond with only a JSON object that matches this JSON schema: no prose, no code fences.\n"
)


def _cost(model: str, usage: Usage) -> float | None:
    price = next((p for key, p in PRICES.items() if key in model), None)
    if price is None:
        return None
    return (usage.input_tokens * price[0] + usage.output_tokens * price[1]) / 1_000_000


class BedrockConverseProvider:
    name = "bedrock-converse"

    def __init__(self, region: str, *, timeout_s: float = 60.0, client: Any = None) -> None:
        # Retries are the router's job, so botocore's own retry loop is off (max_attempts=1).
        self._client = client or boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(read_timeout=timeout_s, connect_timeout=10, retries={"max_attempts": 1}),
        )

    async def complete(self, model: str, request: LLMRequest) -> LLMResponse:
        system = [{"text": block.text} for block in request.system]
        if request.output is not None:
            schema = json.dumps(strict_json_schema(request.output))
            system.append({"text": JSON_INSTRUCTION + schema})
        inference: dict[str, Any] = {"maxTokens": request.max_tokens}
        if request.temperature is not None:
            inference["temperature"] = request.temperature
        kwargs = {
            "modelId": model,
            "system": system,
            "messages": [
                {"role": m.role, "content": [{"text": m.content}]} for m in request.messages
            ],
            "inferenceConfig": inference,
        }

        started = time.perf_counter()
        try:
            response = await asyncio.to_thread(lambda: self._client.converse(**kwargs))
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            raise LLMError(
                f"{self.name} {code}: {exc}",
                retryable=code in RETRYABLE_CODES or (status or 0) >= 500 or status == 429,
                status=status,
            ) from exc
        except (ReadTimeoutError, ConnectionError) as exc:
            raise LLMError(f"{self.name}: {exc}", retryable=True) from exc
        except BotoCoreError as exc:  # e.g. no credentials: a config error, not transient
            raise LLMError(f"{self.name}: {exc}", retryable=False) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        # Reasoning models (gpt-oss, R1) return reasoningContent blocks before the answer text.
        blocks = response.get("output", {}).get("message", {}).get("content", [])
        text = "".join(b["text"] for b in blocks if "text" in b)
        if not text:
            raise LLMError(f"{self.name}: empty completion", retryable=True)

        u = response.get("usage", {})
        usage = Usage(
            input_tokens=int(u.get("inputTokens", 0)),
            output_tokens=int(u.get("outputTokens", 0)),
            cache_read_tokens=int(u.get("cacheReadInputTokens", 0)),
        )
        usage.cost_usd = _cost(model, usage)
        return LLMResponse(
            text=text, usage=usage, provider=self.name, model=model, latency_ms=latency_ms
        )
