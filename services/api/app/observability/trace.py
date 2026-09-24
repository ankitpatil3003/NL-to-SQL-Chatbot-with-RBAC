"""Per-turn trace (CLAUDE.md §4.2 step 11): what the model saw, what it did, what it cost.

One row in app.turn_traces per assistant turn: headline columns for querying (status, model,
SQL, tokens, cost, latency) and a JSONB `detail` with everything else (stage timings, every LLM
attempt incl. fallbacks, retrieval hits with their retriever ranks, entity hints, SQL attempts
with guard/database errors and autofixes).
"""

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.llm.router import RoutedResponse


@dataclass(slots=True)
class TurnTrace:
    user_id: str
    question: str
    prompt_version: str
    session_id: str | None = None
    status: str = "error"
    error: str | None = None
    stages_ms: dict[str, int] = field(default_factory=dict)
    llm_calls: list[dict[str, Any]] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)
    sql_generated: str | None = None
    sql_executed: str | None = None
    row_count: int | None = None
    started: float = field(default_factory=time.perf_counter)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            self.stages_ms[name] = int((time.perf_counter() - started) * 1000)

    def add_llm(self, task: str, routed: RoutedResponse) -> None:
        r = routed.response
        self.llm_calls.append(
            {
                "task": task,
                "provider": r.provider,
                "model": r.model,
                "latency_ms": r.latency_ms,
                "input_tokens": r.usage.input_tokens,
                "output_tokens": r.usage.output_tokens,
                "cache_read_tokens": r.usage.cache_read_tokens,
                "cost_usd": r.usage.cost_usd,
                "fell_back": routed.fell_back,
                "attempts": [asdict(a) for a in routed.attempts],
            }
        )

    @property
    def latency_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)

    def totals(self) -> dict[str, Any]:
        costs = [c["cost_usd"] for c in self.llm_calls]
        return {
            "input_tokens": sum(c["input_tokens"] for c in self.llm_calls),
            "output_tokens": sum(c["output_tokens"] for c in self.llm_calls),
            "cost_usd": None if any(c is None for c in costs) else round(sum(costs), 6),
        }


INSERT = text(
    "INSERT INTO app.turn_traces (user_id, session_id, message_id, status, question, "
    "prompt_version, provider, model, sql_generated, sql_executed, row_count, latency_ms, "
    "input_tokens, output_tokens, cost_usd, detail) VALUES (:user_id, CAST(:session_id AS uuid), "
    "CAST(:message_id AS uuid), :status, :question, :prompt_version, :provider, :model, "
    ":sql_generated, :sql_executed, :row_count, :latency_ms, :input_tokens, :output_tokens, "
    ":cost_usd, CAST(:detail AS jsonb)) RETURNING trace_id"
)


async def save_trace(engine: AsyncEngine, trace: TurnTrace, message_id: str | None = None) -> str:
    sql_call = next((c for c in reversed(trace.llm_calls) if c["task"] == "sql"), None)
    detail = {
        **trace.detail,
        "error": trace.error,
        "stages_ms": trace.stages_ms,
        "llm_calls": trace.llm_calls,
    }
    params = {
        "user_id": trace.user_id,
        "session_id": trace.session_id,
        "message_id": message_id,
        "status": trace.status,
        "question": trace.question,
        "prompt_version": trace.prompt_version,
        "provider": sql_call["provider"] if sql_call else None,
        "model": sql_call["model"] if sql_call else None,
        "sql_generated": trace.sql_generated,
        "sql_executed": trace.sql_executed,
        "row_count": trace.row_count,
        "latency_ms": trace.latency_ms,
        **trace.totals(),
        "detail": json.dumps(detail, default=str),
    }
    async with engine.begin() as conn:
        trace_id = await conn.scalar(INSERT, params)
    return str(trace_id)
