"""Scripted LLM for pipeline tests: responses are queued per task, so a test states exactly what
each stage "returns" and the pipeline's own logic is what gets tested."""

import json
from collections import defaultdict
from typing import Any

from pydantic import BaseModel

from app.llm.base import LLMRequest, LLMResponse, Usage
from app.llm.router import LLMRouter, Target


class ScriptedProvider:
    name = "fake"

    def __init__(self) -> None:
        self.queues: dict[str, list[Any]] = defaultdict(list)
        self.requests: list[LLMRequest] = []

    def add(self, task: str, response: BaseModel | dict[str, Any] | str | Exception) -> None:
        self.queues[task].append(response)

    async def complete(self, model: str, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self.queues[request.task]:
            raise AssertionError(f"no scripted response left for task {request.task!r}")
        item = self.queues[request.task].pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, BaseModel):
            item = item.model_dump_json()
        elif isinstance(item, dict):
            item = json.dumps(item)
        return LLMResponse(text=item, usage=Usage(input_tokens=100, output_tokens=20, cost_usd=0.0),
                           provider="fake", model=model, latency_ms=1)  # fmt: skip

    def last(self, task: str) -> LLMRequest:
        return next(r for r in reversed(self.requests) if r.task == task)


def scripted_router() -> tuple[LLMRouter, ScriptedProvider]:
    provider = ScriptedProvider()
    return LLMRouter({"fake": provider}, {"default": [Target("fake", "m")]}, backoff_s=0), provider
