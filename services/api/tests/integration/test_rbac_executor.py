"""Leak tests for the database security boundary (layer L4), with no LLM involved.

Needs the full generated dataset (uv run scripts/load_data.py --full). Scope assertions are
checked against ground truth computed independently with the owner connection.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor, QueryFailed
from app.rbac.context import Role, UserContext, build_user_context

# What every scoped query in this file is really asking: which territories can this user reach?
TERRITORIES_VIA_SALES = """
    SELECT z.territory_name, count(*) AS n
    FROM sales s JOIN organizations o ON o.org_id = s.org_id JOIN zip_territory z ON z.zip = o.zip
    GROUP BY 1
"""
TERRITORIES_VIA_ORGS = """
    SELECT DISTINCT z.territory_name FROM organizations o JOIN zip_territory z ON z.zip = o.zip
"""


@pytest.fixture
async def owner(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = build_engine(settings)
    yield engine
    await engine.dispose()


@pytest.fixture
async def executor(settings: Settings) -> AsyncIterator[QueryExecutor]:
    ex = QueryExecutor(settings)
    yield ex
    await ex.dispose()


async def all_users(owner: AsyncEngine) -> list[UserContext]:
    async with owner.connect() as conn:
        rows = await conn.execute(text("SELECT * FROM public.users ORDER BY user_id"))
        return [build_user_context(dict(r)) for r in rows.mappings()]


async def user(owner: AsyncEngine, role: Role) -> UserContext:
    return next(u for u in await all_users(owner) if u.role is role)


async def ground_truth(owner: AsyncEngine, u: UserContext) -> dict[str, int]:
    """Sales rows per territory the user is entitled to, computed on the base tables."""
    where = ""
    if u.scope is not None:
        column = "territory_name" if u.scope.level == "territory" else "region_name"
        where = f"WHERE z.{column} = :value"
    sql = f"""SELECT z.territory_name, count(*) FROM public.sales s
              JOIN public.organizations o ON o.org_id = s.org_id
              JOIN public.zip_territory z ON z.zip = o.zip {where} GROUP BY 1"""
    async with owner.connect() as conn:
        rows = await conn.execute(text(sql), {"value": u.scope.value if u.scope else None})
        return {name: n for name, n in rows.all()}


async def entitled_org_count(owner: AsyncEngine, u: UserContext) -> int:
    where = ""
    if u.scope is not None:
        column = "territory_name" if u.scope.level == "territory" else "region_name"
        where = f"WHERE z.{column} = :value"
    sql = f"""SELECT count(*) FROM public.organizations o
              JOIN public.zip_territory z ON z.zip = o.zip {where}"""
    async with owner.connect() as conn:
        result = await conn.execute(text(sql), {"value": u.scope.value if u.scope else None})
        return int(result.scalar_one())


# --- Row-level security -------------------------------------------------------------------------


async def test_every_user_sees_exactly_their_entitled_rows(
    owner: AsyncEngine, executor: QueryExecutor
) -> None:
    users = await all_users(owner)
    assert len(users) == 23
    for u in users:
        expected = await ground_truth(owner, u)
        got = dict((await executor.run(u, TERRITORIES_VIA_SALES)).rows)
        assert got == expected, f"{u.user_id} {u.role} {u.scope}"

        orgs = {r[0] for r in (await executor.run(u, TERRITORIES_VIA_ORGS)).rows}
        assert orgs == set(expected), f"{u.user_id} organizations"

        # Each view queried on its own, with no joins. A join through the other view would hide a
        # missing filter here (a mutation test caught exactly that blind spot).
        sales_only = (await executor.run(u, "SELECT count(*) FROM sales")).rows[0][0]
        assert sales_only == sum(expected.values()), f"{u.user_id} sales alone"
        orgs_only = (await executor.run(u, "SELECT count(*) FROM organizations")).rows[0][0]
        assert orgs_only == await entitled_org_count(owner, u), f"{u.user_id} organizations alone"

    # Sanity: the expectations themselves are meaningful.
    exec_user = next(u for u in users if u.role is Role.EXEC)
    assert len(await ground_truth(owner, exec_user)) == 15


async def test_market_data_follows_the_same_scope(
    owner: AsyncEngine, executor: QueryExecutor
) -> None:
    ram = await user(owner, Role.RAM)
    sql = TERRITORIES_VIA_SALES.replace("GROUP BY", "WHERE s.data_source = 'market_data' GROUP BY")
    got = {r[0] for r in (await executor.run(ram, sql)).rows}
    assert got == {ram.territory}


async def test_explicit_filter_for_another_territory_returns_nothing(
    owner: AsyncEngine, executor: QueryExecutor
) -> None:
    ram = await user(owner, Role.RAM)
    other = "Texas" if ram.territory != "Texas" else "Mountain"
    sql = f"""SELECT count(*) FROM sales s JOIN organizations o ON o.org_id = s.org_id
              JOIN zip_territory z ON z.zip = o.zip WHERE z.territory_name = '{other}'"""
    assert (await executor.run(ram, sql)).rows == [(0,)]


# --- Column-level security (WAC) ----------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.RAM, Role.DIRECTOR])
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT sum(wac) FROM sales",
        "SELECT s.wac FROM sales s LIMIT 1",
        "SELECT count(*) FROM sales WHERE wac > 0",
        "SELECT org_id FROM sales ORDER BY wac DESC LIMIT 1",
    ],
)
async def test_non_exec_cannot_reference_wac(
    owner: AsyncEngine, executor: QueryExecutor, role: Role, sql: str
) -> None:
    with pytest.raises(QueryFailed) as err:
        await executor.run(await user(owner, role), sql)
    assert err.value.sqlstate == "42703"  # undefined_column: it doesn't exist for them


@pytest.mark.parametrize("role", [Role.RAM, Role.DIRECTOR])
async def test_select_star_has_no_wac_column(
    owner: AsyncEngine, executor: QueryExecutor, role: Role
) -> None:
    result = await executor.run(await user(owner, role), "SELECT * FROM sales LIMIT 1")
    assert "wac" not in result.columns
    assert "pack_units" in result.columns


async def test_exec_sees_wac(owner: AsyncEngine, executor: QueryExecutor) -> None:
    result = await executor.run(await user(owner, Role.EXEC), "SELECT sum(wac) FROM sales")
    assert result.rows[0][0] > 0


# --- Escape attempts ------------------------------------------------------------------------------

ESCAPES = [
    "SELECT set_config('role', 'pharma', true)",
    "SELECT set_config('role', 'nl2sql_exec_reader', true)",
    "SET ROLE nl2sql_exec_reader",
    "SELECT rbac.set_scope('territory', 'Texas')",
    "SELECT count(*) FROM public.sales",
    "SELECT count(*) FROM public.organizations",
    "SELECT * FROM users",
    "SELECT * FROM app.chat_messages",
    "SELECT * FROM app.credentials",
    "UPDATE pg_temp.rbac_scope SET value = 'Texas'",
    "DELETE FROM products",
    "CREATE TEMP TABLE x (i int)",
    "SELECT 1; SELECT 2",
    "COPY (SELECT 1) TO PROGRAM 'id'",
    "SELECT set_config('transaction_read_only', 'off', true)",
]


@pytest.mark.parametrize("role", [Role.RAM, Role.DIRECTOR])
@pytest.mark.parametrize("sql", ESCAPES)
async def test_scoped_reader_escapes_are_blocked(
    owner: AsyncEngine, executor: QueryExecutor, role: Role, sql: str
) -> None:
    with pytest.raises(QueryFailed):
        await executor.run(await user(owner, role), sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM users",
        "SELECT * FROM app.chat_messages",
        "SELECT set_config('role', 'pharma', true)",
        "DELETE FROM products",
    ],
)
async def test_exec_reader_is_also_least_privilege(
    owner: AsyncEngine, executor: QueryExecutor, sql: str
) -> None:
    with pytest.raises(QueryFailed):
        await executor.run(await user(owner, Role.EXEC), sql)


async def test_scope_seal_survives_a_failed_escape_in_the_same_session(
    owner: AsyncEngine, executor: QueryExecutor
) -> None:
    """After a blocked attempt, the next query on a pooled connection is still correctly scoped."""
    ram = await user(owner, Role.RAM)
    with pytest.raises(QueryFailed):
        await executor.run(ram, "SELECT rbac.set_scope('territory', 'Texas')")
    got = {r[0] for r in (await executor.run(ram, TERRITORIES_VIA_SALES)).rows}
    assert got == {ram.territory}


# --- Resource limits ----------------------------------------------------------------------------


async def test_statement_timeout_kills_runaway_queries(
    owner: AsyncEngine, settings: Settings
) -> None:
    ex = QueryExecutor(settings.model_copy(update={"query_timeout_ms": 300}))
    try:
        with pytest.raises(QueryFailed) as err:
            await ex.run(await user(owner, Role.EXEC), "SELECT pg_sleep(5)")
        assert err.value.sqlstate == "57014"  # query_canceled
    finally:
        await ex.dispose()


async def test_row_limit_truncates(owner: AsyncEngine, settings: Settings) -> None:
    ex = QueryExecutor(settings.model_copy(update={"query_row_limit": 10}))
    try:
        result = await ex.run(await user(owner, Role.RAM), "SELECT org_id FROM organizations")
        assert len(result.rows) == 10 and result.truncated
    finally:
        await ex.dispose()
