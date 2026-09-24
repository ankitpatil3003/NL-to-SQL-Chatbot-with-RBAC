"""End-to-end turns with a scripted model against the real database, retrieval, guard and
executor: every path through the pipeline, the event stream, and the persisted trace."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor
from app.knowledge.base import init_knowledge
from app.llm.base import LLMError
from app.nl2sql.generate import WAC_REDACTED, WAC_SQL
from app.nl2sql.pipeline import FAILED, UNAVAILABLE, Pipeline, ask
from app.nl2sql.types import HistoryTurn, Mention, SqlDraft, Understanding

from ..fakes import ScriptedProvider, scripted_router
from ..unit.test_sqlguard import EXEC, RAM

UNITS_SQL = (
    "SELECT drug_name, SUM(pack_units) AS total_units FROM sales "
    "WHERE data_source = 'distributor' AND brand_flag = 1 GROUP BY 1 ORDER BY 2 DESC"
)


def understood(question: str, intent: str = "data_question", **kw: object) -> Understanding:
    fields: dict[str, object] = {
        "intent": intent, "standalone_question": question, "is_follow_up": False,
        "asks_for_dollars": False, "mentions": [], "reply": "", "title": "",
    }  # fmt: skip
    return Understanding.model_validate(fields | kw)


def draft(sql: str) -> SqlDraft:
    return SqlDraft(answerable=True, sql=sql, rules_applied=["DS-1"],
                    assumptions=["All available history."], unanswerable_reason="")  # fmt: skip


@pytest.fixture
async def env(settings: Settings) -> AsyncIterator[tuple[Pipeline, ScriptedProvider, AsyncEngine]]:
    engine = build_engine(settings)
    executor = QueryExecutor(settings)
    kb = await init_knowledge(engine, settings.knowledge_docs_dir, settings.embed_cache_dir)
    assert kb is not None
    llm, fake = scripted_router()
    yield Pipeline(llm, kb, executor, engine, max_rows=1000), fake, engine
    await executor.dispose()
    await engine.dispose()


async def trace_row(engine: AsyncEngine, trace_id: str | None) -> dict[str, object]:
    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT * FROM app.turn_traces WHERE trace_id = CAST(:id AS uuid)"),
            {"id": trace_id},
        )
        return dict(row.mappings().one())


async def test_full_data_turn_streams_events_and_persists_a_trace(env) -> None:  # type: ignore[no-untyped-def]
    pipeline, fake, engine = env
    fake.add(
        "router", understood("Units by drug?", mentions=[Mention(kind="drug", text="zenovax")])
    )
    fake.add("sql", draft(UNITS_SQL))
    fake.add("answer", "ZENOVAX leads with 1.2M units.")

    events = [e async for e in pipeline.run("units by drug?", [], RAM)]
    assert [e.data for e in events if e.type == "stage"] == [
        "understanding",
        "retrieving",
        "writing_sql",
        "answering",
    ]
    assert [e.type for e in events][-2:] == ["answer_delta", "result"]
    result = events[-1].data
    assert result.status == "answered" and result.table.rows and "LIMIT 1000" in result.sql

    row = await trace_row(engine, result.trace_id)
    assert row["status"] == "answered" and row["row_count"] == result.table.row_count
    assert row["prompt_version"] == pipeline.prompt_version and row["sql_executed"] == result.sql
    detail = row["detail"]
    assert [c["task"] for c in detail["llm_calls"]] == ["router", "sql", "answer"]  # type: ignore[index]
    assert detail["retrieval"]["docs"] and detail["retrieval"]["examples"]  # type: ignore[index]
    assert detail["entities"] == ["- \"zenovax\" (drug) -> drug_name = 'ZENOVAX'"]  # type: ignore[index]


async def test_ram_prompt_never_contains_wac_examples(env) -> None:  # type: ignore[no-untyped-def]
    pipeline, fake, _ = env
    question = "What is our revenue in dollars by product this year?"
    fake.add("router", understood(question, asks_for_dollars=True))
    fake.add("sql", draft(UNITS_SQL))
    fake.add("answer", "Here is volume instead.")
    result = await ask(pipeline, question, [], RAM)
    prompt_text = fake.last("sql").messages[0].content
    assert not WAC_SQL.search(prompt_text), "RAM prompt shows SQL that uses wac"
    assert "WAC" in prompt_text or WAC_REDACTED in prompt_text  # prose/redaction, not patterns
    assert any("WAC" in n and "unit volume" in n for n in result.notes)


async def test_exec_prompt_gets_wac_examples(env) -> None:  # type: ignore[no-untyped-def]
    pipeline, fake, _ = env
    question = "What is our revenue in dollars by product this year?"
    fake.add("router", understood(question, asks_for_dollars=True))
    fake.add("sql", draft("SELECT drug_name, SUM(wac) AS revenue FROM sales GROUP BY 1"))
    fake.add("answer", "Revenue by product...")
    result = await ask(pipeline, question, [], EXEC)
    assert "sum(s.wac)" in fake.last("sql").messages[0].content.lower() and not result.notes


@pytest.mark.parametrize(
    ("intent", "status"),
    [("smalltalk", "answered"), ("out_of_scope", "refused"), ("clarify", "clarification")],
)
async def test_non_data_intents_answer_without_sql(env, intent: str, status: str) -> None:  # type: ignore[no-untyped-def]
    pipeline, fake, engine = env
    fake.add(
        "router", understood("hi", intent=intent, reply="Hello! I can help with sales questions.")
    )
    result = await ask(pipeline, "hi", [], RAM)
    assert result.status == status and result.answer.startswith("Hello") and result.sql is None
    assert not [r for r in fake.requests if r.task == "sql"]
    assert (await trace_row(engine, result.trace_id))["status"] == status


async def test_follow_up_sends_previous_sql(env) -> None:  # type: ignore[no-untyped-def]
    pipeline, fake, _ = env
    history = [HistoryTurn("units by drug", "ZENOVAX leads...", sql=UNITS_SQL)]
    fake.add("router", understood("Units by drug by quarter", is_follow_up=True))
    fake.add("sql", draft(UNITS_SQL))
    fake.add("answer", "By quarter...")
    await ask(pipeline, "now by quarter", history, RAM)
    assert "Previous question and its SQL" in fake.last("sql").messages[0].content


async def test_model_outage_is_reported_and_traced(env) -> None:  # type: ignore[no-untyped-def]
    pipeline, fake, engine = env
    fake.add("router", LLMError("503", retryable=True))
    fake.add("router", LLMError("503", retryable=True))
    result = await ask(pipeline, "units?", [], RAM)
    assert result.status == "error" and result.answer == UNAVAILABLE
    row = await trace_row(engine, result.trace_id)
    assert row["status"] == "error" and "all models failed" in row["detail"]["error"]  # type: ignore[index]


async def test_exhausted_repairs_give_a_graceful_answer(env) -> None:  # type: ignore[no-untyped-def]
    pipeline, fake, engine = env
    fake.add("router", understood("users?"))
    for _ in range(3):
        fake.add("sql", draft("SELECT * FROM users"))
    result = await ask(pipeline, "users?", [], RAM)
    assert result.status == "error" and result.answer == FAILED
    attempts = (await trace_row(engine, result.trace_id))["detail"]["sql_attempts"]  # type: ignore[index]
    assert len(attempts) == 3 and all(a["failed_at"] == "guard" for a in attempts)
