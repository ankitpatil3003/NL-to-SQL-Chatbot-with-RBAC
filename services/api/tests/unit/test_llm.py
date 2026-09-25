"""LLM layer: wire formats, error classification, structured output, routing and fallback.
No network: httpx MockTransport for the OpenAI-compatible API, a stub for the Anthropic SDK."""

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import (
    LLMError,
    LLMRequest,
    LLMResponse,
    Message,
    SystemBlock,
    Usage,
    parse_json_output,
    strict_json_schema,
)
from app.llm.factory import build_router
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.router import LLMRouter, LLMUnavailable, Target


class SqlOut(BaseModel):
    sql: str
    notes: list[str]


def request(output: type[BaseModel] | None = None, task: str = "sql") -> LLMRequest:
    return LLMRequest(
        task=task,
        system=[SystemBlock("rules", cache=True), SystemBlock("user scope")],
        messages=[Message("user", "top accounts?")],
        output=output,
    )


# --- helpers ----------------------------------------------------------------------------------


def test_target_parse_keeps_colons_in_model_ids() -> None:
    t = Target.parse(" openrouter:qwen/qwen3.8-27b:free ")
    assert (t.provider, t.model) == ("openrouter", "qwen/qwen3.8-27b:free")
    with pytest.raises(ValueError):
        Target.parse("no-provider")


def test_strict_schema_closes_every_object() -> None:
    class Inner(BaseModel):
        a: int

    class Outer(BaseModel):
        inner: Inner
        tags: list[str]

    schema = strict_json_schema(Outer)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"inner", "tags"}
    inner = schema["$defs"]["Inner"]
    assert inner["additionalProperties"] is False and inner["required"] == ["a"]


@pytest.mark.parametrize(
    "text",
    [
        '{"sql": "SELECT 1", "notes": []}',
        '```json\n{"sql": "SELECT 1", "notes": []}\n```',
        'Here you go:\n{"sql": "SELECT 1", "notes": []}\nHope that helps!',
    ],
)
def test_parse_json_output_tolerates_fences_and_chatter(text: str) -> None:
    assert parse_json_output(text) == {"sql": "SELECT 1", "notes": []}


# --- OpenAI-compatible provider ----------------------------------------------------------------


def compat(handler: Any) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        "openrouter", "https://example.test/v1", "key-123",
        extra_body={"usage": {"include": True}}, transport=httpx.MockTransport(handler),
    )  # fmt: skip


def ok_payload(content: str, **usage: Any) -> dict[str, Any]:
    return {
        "model": "m",
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, **usage},
    }


async def test_compat_request_shape_and_usage_parsing() -> None:
    seen: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["auth"] = req.headers["authorization"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=ok_payload('{"sql":"SELECT 1","notes":[]}', cost=0.0012))

    resp = await compat(handler).complete("vendor/model", request(SqlOut))
    body = seen["body"]
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["auth"] == "Bearer key-123"
    assert body["messages"][0] == {"role": "system", "content": "rules\n\nuser scope"}
    assert body["messages"][1] == {"role": "user", "content": "top accounts?"}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["usage"] == {"include": True}
    assert (resp.usage.input_tokens, resp.usage.output_tokens, resp.usage.cost_usd) == (
        100,
        20,
        0.0012,
    )


async def test_compat_free_model_without_reported_cost_is_zero() -> None:
    provider = compat(lambda r: httpx.Response(200, json=ok_payload("hi")))
    assert (await provider.complete("x/y:free", request())).usage.cost_usd == 0.0


@pytest.mark.parametrize(
    ("response", "retryable"),
    [
        (httpx.Response(429, text="slow down"), True),
        (httpx.Response(503, text="unavailable"), True),
        (httpx.Response(400, text="bad request"), False),
        (httpx.Response(401, text="bad key"), False),
        (httpx.Response(200, json={"error": {"code": 502, "message": "upstream"}}), True),
        (httpx.Response(200, json={"error": {"code": 400, "message": "context too long"}}), False),
        (httpx.Response(200, json=ok_payload("")), True),  # reasoning model spent budget thinking
    ],
)
async def test_compat_error_classification(response: httpx.Response, retryable: bool) -> None:
    with pytest.raises(LLMError) as err:
        await compat(lambda r: response).complete("m", request())
    assert err.value.retryable is retryable


async def test_compat_timeout_is_retryable() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(LLMError) as err:
        await compat(handler).complete("m", request())
    assert err.value.retryable


# --- Anthropic provider --------------------------------------------------------------------------


class StubMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return self.response


def anthropic_response(stop_reason: str = "end_turn") -> Any:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text='{"sql":"SELECT 1","notes":[]}')],
        usage=SimpleNamespace(
            input_tokens=1000, output_tokens=100,
            cache_read_input_tokens=9000, cache_creation_input_tokens=0,
        ),
    )  # fmt: skip


async def test_anthropic_caches_stable_system_blocks_and_requests_json_schema() -> None:
    messages = StubMessages(anthropic_response())
    provider = AnthropicProvider("k", client=SimpleNamespace(messages=messages))
    resp = await provider.complete("claude-sonnet-5", request(SqlOut))

    system = messages.kwargs["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in system[1]  # per-user block stays out of the cached prefix
    assert messages.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert resp.usage.cache_read_tokens == 9000
    # 1000*2 + 9000*2*0.1 + 100*10 = 4800 micro-dollars
    assert resp.usage.cost_usd == pytest.approx(0.0048)


async def test_bedrock_gets_json_from_a_forced_tool_call() -> None:
    # Bedrock has no output_config structured outputs: the schema goes in as a forced tool.
    response = anthropic_response("tool_use")
    response.content = [SimpleNamespace(type="tool_use", input={"sql": "SELECT 1", "notes": []})]
    messages = StubMessages(response)
    provider = AnthropicProvider(
        client=SimpleNamespace(messages=messages), name="bedrock", json_via_tool=True
    )
    resp = await provider.complete("anthropic.claude-sonnet-5", request(SqlOut))

    assert "output_config" not in messages.kwargs
    assert messages.kwargs["tool_choice"] == {"type": "tool", "name": "emit_result"}
    assert messages.kwargs["tools"][0]["input_schema"]["additionalProperties"] is False
    assert json.loads(resp.text) == {"sql": "SELECT 1", "notes": []}
    assert resp.provider == "bedrock"
    assert resp.usage.cost_usd == pytest.approx(0.0048)  # `anthropic.` prefix priced


def test_factory_registers_bedrock_only_when_a_region_is_set() -> None:
    from app.llm.factory import build_providers

    base = {"_env_file": None, "openrouter_api_key": None, "anthropic_api_key": None}
    assert "bedrock" not in build_providers(Settings(**base))  # type: ignore[arg-type]
    providers = build_providers(Settings(**base, bedrock_region="us-east-2"))  # type: ignore[arg-type]
    assert providers["bedrock"].name == "bedrock"


async def test_anthropic_refusal_is_not_retryable() -> None:
    provider = AnthropicProvider(
        "k", client=SimpleNamespace(messages=StubMessages(anthropic_response("refusal")))
    )
    with pytest.raises(LLMError) as err:
        await provider.complete("claude-sonnet-5", request())
    assert not err.value.retryable


# --- Router ---------------------------------------------------------------------------------------


class FakeProvider:
    """Plays back a script: each item is a text to return or an exception to raise."""

    def __init__(self, name: str, script: list[str | Exception]) -> None:
        self.name = name
        self.script = list(script)
        self.calls: list[str] = []

    async def complete(self, model: str, req: LLMRequest) -> LLMResponse:
        self.calls.append(model)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return LLMResponse(text=item, usage=Usage(), provider=self.name, model=model, latency_ms=1)


GOOD = '{"sql": "SELECT 1", "notes": []}'
RATE_LIMITED = LLMError("429", retryable=True, status=429)


def router(*providers: FakeProvider, chains: dict[str, list[str]] | None = None) -> LLMRouter:
    specs = chains or {"default": [f"{p.name}:model" for p in providers]}
    return LLMRouter(
        {p.name: p for p in providers},
        {task: [Target.parse(s) for s in chain] for task, chain in specs.items()},
        backoff_s=0,
    )


async def test_first_target_success() -> None:
    a = FakeProvider("a", [GOOD])
    routed = await router(a).complete(request(SqlOut))
    assert isinstance(routed.response.data, SqlOut) and not routed.fell_back


async def test_retryable_error_retries_then_falls_back() -> None:
    a, b = FakeProvider("a", [RATE_LIMITED, RATE_LIMITED]), FakeProvider("b", [GOOD])
    routed = await router(a, b).complete(request(SqlOut))
    assert len(a.calls) == 2 and len(b.calls) == 1
    assert routed.fell_back and routed.response.provider == "b"
    assert [x.ok for x in routed.attempts] == [False, False, True]


async def test_non_retryable_error_skips_straight_to_next_target() -> None:
    a, b = FakeProvider("a", [LLMError("401", retryable=False)]), FakeProvider("b", [GOOD])
    await router(a, b).complete(request(SqlOut))
    assert len(a.calls) == 1  # no pointless retry of a bad key


async def test_invalid_structured_output_counts_as_retryable_failure() -> None:
    a = FakeProvider("a", ["not json at all", '{"sql": "SELECT 1"}'])  # 2nd misses `notes`
    b = FakeProvider("b", [GOOD])
    routed = await router(a, b).complete(request(SqlOut))
    assert routed.response.provider == "b"
    assert "JSONDecodeError" in (routed.attempts[0].error or "")
    assert "ValidationError" in (routed.attempts[1].error or "")


async def test_all_targets_failing_raises_with_every_attempt() -> None:
    a, b = FakeProvider("a", [RATE_LIMITED] * 2), FakeProvider("b", [RATE_LIMITED] * 2)
    with pytest.raises(LLMUnavailable) as err:
        await router(a, b).complete(request())
    assert len(err.value.attempts) == 4


async def test_task_specific_chain_overrides_default() -> None:
    a, b = FakeProvider("a", []), FakeProvider("b", ["a title"])
    r = router(a, b, chains={"default": ["a:m"], "title": ["b:small"]})
    routed = await r.complete(request(task="title"))
    assert routed.response.provider == "b" and b.calls == ["small"]


def test_router_rejects_chains_with_unconfigured_providers() -> None:
    with pytest.raises(ValueError, match="unconfigured"):
        LLMRouter({}, {"default": [Target.parse("ghost:model")]})


# --- Factory ---------------------------------------------------------------------------------------


def test_factory_disables_assistant_without_keys_and_skips_unkeyed_targets() -> None:
    assert build_router(Settings(openrouter_api_key=None, anthropic_api_key=None)) is None

    r = build_router(
        Settings(
            openrouter_api_key="k",
            anthropic_api_key=None,
            llm_chain="anthropic:claude-sonnet-5,openrouter:qwen/qwen3.8-27b:free",
        )
    )
    assert r is not None
    assert [str(t) for t in r.chain_for("sql")] == ["openrouter:qwen/qwen3.8-27b:free"]
