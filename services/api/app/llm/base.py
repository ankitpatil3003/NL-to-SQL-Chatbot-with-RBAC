"""Provider-neutral LLM types. Everything above app/llm talks in these, never in a vendor SDK's
types, so a model or provider change is configuration (LLM_CHAIN), not code."""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel


class LLMError(Exception):
    """A provider call failed. `retryable` decides between retry/fallback and giving up at once
    (rate limits, 5xx, timeouts, malformed structured output: retryable; bad request or bad
    credentials: the same request would fail everywhere, or is a config error)."""

    def __init__(self, message: str, *, retryable: bool, status: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status = status


@dataclass(frozen=True, slots=True)
class SystemBlock:
    text: str
    # Stable content (instructions, the semantic contract) is marked cacheable. Providers with
    # explicit prompt caching (Anthropic) put a breakpoint after it; others cache automatically
    # or ignore it.
    cache: bool = False


@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    task: str  # routing key: "sql", "router", "rewrite", "answer", "title"
    system: list[SystemBlock]
    messages: list[Message]
    max_tokens: int = 4096
    temperature: float | None = 0.0
    # When set, the provider is asked for JSON matching this model's schema and the router
    # validates the result; a response that doesn't validate counts as a retryable failure.
    output: type[BaseModel] | None = None


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float | None = None  # None = unknown; free models report 0.0


@dataclass(slots=True)
class LLMResponse:
    text: str
    usage: Usage
    provider: str
    model: str
    latency_ms: int
    data: BaseModel | None = None  # validated structured output, when requested
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


class Provider(Protocol):
    name: str

    async def complete(self, model: str, request: LLMRequest) -> LLMResponse: ...


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON schema in the strict shape structured-output APIs require: every object closed
    (additionalProperties: false) and every property listed in `required`."""
    schema = model.model_json_schema()

    def close(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for item in node:
                close(item)

    close(schema)
    return schema


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def parse_json_output(text: str) -> Any:
    """Tolerant JSON extraction. Some (especially free) models wrap JSON in ``` fences or add a
    sentence around it even when a schema was requested."""
    candidate = text.strip()
    if fenced := _FENCE.match(candidate):
        candidate = fenced.group(1)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(candidate[start : end + 1])
