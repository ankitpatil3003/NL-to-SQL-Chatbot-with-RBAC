"""Model routing with retry and fallback.

A *chain* is an ordered list of provider:model targets per task, from configuration, e.g.
    LLM_CHAIN = "openrouter:nvidia/nemotron-3-super-120b-a12b:free,openrouter:qwen/qwen3.8-27b:free"
For each request: try the first target; on a retryable failure retry it once (short backoff),
then move to the next target. Non-retryable failures skip straight to the next target (a 401 on
one provider says nothing about another). Every attempt is recorded for the turn trace.
"""

import asyncio
import time
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.llm.base import LLMError, LLMRequest, LLMResponse, Provider, parse_json_output


@dataclass(frozen=True, slots=True)
class Target:
    provider: str
    model: str

    @classmethod
    def parse(cls, spec: str) -> "Target":
        """'openrouter:qwen/qwen3.8-27b:free' -> provider 'openrouter', model 'qwen/...:free'.
        Only the first colon separates: model ids may contain colons."""
        provider, sep, model = spec.strip().partition(":")
        if not sep or not provider or not model:
            raise ValueError(f"invalid LLM target {spec!r}; expected provider:model")
        return cls(provider, model)

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass(frozen=True, slots=True)
class Attempt:
    target: str
    ok: bool
    latency_ms: int
    error: str | None = None


@dataclass(slots=True)
class RoutedResponse:
    response: LLMResponse
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def fell_back(self) -> bool:
        return len({a.target for a in self.attempts}) > 1


class LLMUnavailable(Exception):
    """Every target in the chain failed."""

    def __init__(self, task: str, attempts: list[Attempt]) -> None:
        detail = "; ".join(f"{a.target}: {a.error}" for a in attempts)
        super().__init__(f"all models failed for task {task!r}: {detail}")
        self.attempts = attempts


class LLMRouter:
    def __init__(
        self,
        providers: dict[str, Provider],
        chains: dict[str, list[Target]],
        *,
        retries_per_target: int = 1,
        backoff_s: float = 0.5,
    ) -> None:
        if "default" not in chains:
            raise ValueError("chains must include a 'default' chain")
        for task, chain in chains.items():
            missing = {t.provider for t in chain} - providers.keys()
            if missing:
                raise ValueError(f"chain {task!r} uses unconfigured providers: {sorted(missing)}")
        self._providers = providers
        self._chains = chains
        self._retries = retries_per_target
        self._backoff_s = backoff_s

    async def aclose(self) -> None:
        for provider in self._providers.values():
            if close := getattr(provider, "aclose", None):
                await close()

    def chain_for(self, task: str) -> list[Target]:
        return self._chains.get(task) or self._chains["default"]

    async def complete(self, request: LLMRequest) -> RoutedResponse:
        attempts: list[Attempt] = []
        for target in self.chain_for(request.task):
            for attempt_no in range(self._retries + 1):
                started = time.perf_counter()
                try:
                    response = await self._providers[target.provider].complete(
                        target.model, request
                    )
                    if request.output is not None:
                        response.data = request.output.model_validate(
                            parse_json_output(response.text)
                        )
                except (LLMError, ValueError, ValidationError) as exc:
                    # ValueError covers JSONDecodeError: malformed structured output is retryable.
                    retryable = exc.retryable if isinstance(exc, LLMError) else True
                    attempts.append(Attempt(str(target), False, _ms(started), _short(exc)))
                    if not retryable:
                        break  # this target won't succeed; move to the next one
                    if attempt_no < self._retries:
                        await asyncio.sleep(self._backoff_s * (attempt_no + 1))
                    continue
                attempts.append(Attempt(str(target), True, _ms(started)))
                return RoutedResponse(response, attempts)
        raise LLMUnavailable(request.task, attempts)


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _short(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}"
