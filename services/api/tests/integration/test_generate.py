"""SQL generation loop with a scripted model against the real guard + database: success, repair
after guard and database errors, exhausting repairs, unanswerable questions, prompt contents."""

from collections.abc import AsyncIterator

import pytest

from app.core.config import Settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor
from app.knowledge.base import KnowledgeBase
from app.knowledge.contract import load_catalog, load_contract
from app.nl2sql.generate import MAX_REPAIRS, build_context, generate_and_run
from app.nl2sql.types import HistoryTurn, SqlDraft

from ..fakes import scripted_router
from ..unit.test_sqlguard import EXEC, RAM

GOOD = "SELECT drug_name, SUM(pack_units) AS total_units FROM sales WHERE data_source = 'distributor' AND brand_flag = 1 GROUP BY 1"


def draft(sql: str, answerable: bool = True, reason: str = "") -> SqlDraft:
    return SqlDraft(
        answerable=answerable,
        sql=sql,
        rules_applied=["DS-1"],
        assumptions=[],
        unanswerable_reason=reason,
    )


@pytest.fixture
async def deps(settings: Settings) -> AsyncIterator[tuple[KnowledgeBase, QueryExecutor]]:
    engine = build_engine(settings)
    executor = QueryExecutor(settings)
    kb = KnowledgeBase(load_contract(), await load_catalog(engine), None)  # type: ignore[arg-type]
    yield kb, executor
    await executor.dispose()
    await engine.dispose()


async def test_first_try_success(deps) -> None:  # type: ignore[no-untyped-def]
    kb, executor = deps
    llm, fake = scripted_router()
    fake.add("sql", draft(GOOD))
    out = await generate_and_run(llm, kb, executor, RAM, "units by drug", max_rows=100)
    assert out.succeeded and len(out.attempts) == 1 and out.result and out.result.rows
    system = fake.last("sql").system
    assert system[0].cache and "[MS-1]" in system[0].text  # contract in the cached block
    assert not system[1].cache and "may NOT see WAC" in system[1].text


async def test_guard_violation_is_repaired_with_the_guards_guidance(deps) -> None:  # type: ignore[no-untyped-def]
    kb, executor = deps
    llm, fake = scripted_router()
    fake.add("sql", draft("SELECT SUM(wac) FROM sales"))  # RAM may not use wac
    fake.add("sql", draft(GOOD))
    out = await generate_and_run(llm, kb, executor, RAM, "revenue by drug", max_rows=100)
    assert out.succeeded and [a.failed_at for a in out.attempts] == ["guard", None]
    feedback = fake.last("sql").messages[-1].content
    assert "rejected by the guard" in feedback and "pack_units" in feedback


async def test_database_error_is_repaired_with_the_postgres_message(deps) -> None:  # type: ignore[no-untyped-def]
    kb, executor = deps
    llm, fake = scripted_router()
    fake.add("sql", draft("SELECT SUM(units) FROM sales"))  # no such column
    fake.add("sql", draft(GOOD))
    out = await generate_and_run(llm, kb, executor, EXEC, "units", max_rows=100)
    assert out.succeeded and out.attempts[0].failed_at == "database"
    assert 'column "units" does not exist' in fake.last("sql").messages[-1].content


async def test_gives_up_after_max_repairs(deps) -> None:  # type: ignore[no-untyped-def]
    kb, executor = deps
    llm, fake = scripted_router()
    for _ in range(MAX_REPAIRS + 1):
        fake.add("sql", draft("SELECT * FROM users"))
    out = await generate_and_run(llm, kb, executor, EXEC, "users?", max_rows=100)
    assert not out.succeeded and len(out.attempts) == MAX_REPAIRS + 1
    assert len(out.llm_calls) == MAX_REPAIRS + 1


async def test_unanswerable_stops_without_running_anything(deps) -> None:  # type: ignore[no-untyped-def]
    kb, executor = deps
    llm, fake = scripted_router()
    fake.add("sql", draft("", answerable=False, reason="Patient outcomes are not in the data."))
    out = await generate_and_run(llm, kb, executor, EXEC, "patient survival rates?", max_rows=100)
    assert out.unanswerable and not out.attempts


def test_context_includes_previous_sql_for_follow_ups() -> None:
    previous = HistoryTurn("top accounts this quarter", "...", sql="SELECT 1")
    ctx = build_context("now by month", docs=[], examples=[], resolutions=[], previous=previous)
    assert "Previous question and its SQL" in ctx and "SELECT 1" in ctx
    assert ctx.rstrip().endswith("now by month")
