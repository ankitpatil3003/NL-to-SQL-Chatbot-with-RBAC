"""Live calls to every model in the configured chain. Skipped unless OPENROUTER_API_KEY is set
(uses the free-tier daily quota: a handful of requests per run).

    OPENROUTER_API_KEY=... uv run pytest tests/live -q -s
"""

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.llm.base import LLMRequest, Message, SystemBlock, parse_json_output
from app.llm.factory import build_providers
from app.llm.router import Target

settings = Settings()  # reads env and .env, exactly like the app
pytestmark = pytest.mark.skipif(
    not settings.openrouter_api_key, reason="live LLM test: set OPENROUTER_API_KEY (env or .env)"
)


class Answer(BaseModel):
    sql: str
    explanation: str


TARGETS = [Target.parse(s) for s in settings.llm_chain.split(",") if s.strip()]


@pytest.mark.parametrize("target", TARGETS, ids=str)
async def test_model_returns_schema_valid_json(target: Target) -> None:
    provider = build_providers(settings)[target.provider]
    request = LLMRequest(
        task="sql",
        system=[
            SystemBlock("You write PostgreSQL. Table sales(drug_name text, pack_units float).")
        ],
        messages=[Message("user", "Total pack units per drug, highest first.")],
        max_tokens=2000,
        output=Answer,
    )
    resp = await provider.complete(target.model, request)
    parsed = Answer.model_validate(parse_json_output(resp.text))
    print(
        f"\n{target}: {resp.latency_ms} ms, in={resp.usage.input_tokens} out={resp.usage.output_tokens} "
        f"cost={resp.usage.cost_usd}\n  sql: {parsed.sql}"
    )
    assert "select" in parsed.sql.lower() and "sales" in parsed.sql.lower()
