"""The guard executes sqlglot's regeneration of the SQL, not the original text. Prove on real data
that regeneration never changes meaning: original and guarded SQL must return identical results."""

from collections.abc import AsyncIterator

import pytest

from app.core.config import Settings
from app.db.executor import QueryExecutor, QueryFailed
from app.rbac.context import UserContext
from app.sqlguard.guard import guard

from ..unit.test_sqlguard import EXEC, RAM, VALID

EXTRA = {
    "fetch first": "SELECT drug_name, SUM(pack_units) AS u FROM sales GROUP BY 1 ORDER BY 2 DESC FETCH FIRST 3 ROWS ONLY",
    "date_trunc + extract": """
        SELECT DATE_TRUNC('month', CAST(transaction_date AS date)) AS m,
               EXTRACT(YEAR FROM CAST(transaction_date AS date)) AS y, COUNT(*)
        FROM sales WHERE mo_offset < 3 GROUP BY 1, 2""",
    "string_agg + percentile": """
        SELECT market_category, STRING_AGG(DISTINCT drug_name, ', ' ORDER BY drug_name) AS drugs,
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY unit_conversion_factor) AS median_ucf
        FROM products GROUP BY market_category""",
    "recursive cte": "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 12) SELECT n FROM r",
    "filter clause + ilike": """
        SELECT COUNT(*) FILTER (WHERE org_name ILIKE '%cancer%') AS cancer_orgs,
               COUNT(*) FILTER (WHERE is_340b = 1) AS b340 FROM organizations""",
}
CORPUS = VALID | EXTRA


@pytest.fixture
async def executor(settings: Settings) -> AsyncIterator[QueryExecutor]:
    ex = QueryExecutor(settings.model_copy(update={"query_row_limit": 100_000}))
    yield ex
    await ex.dispose()


def normalised(rows: list[tuple[object, ...]]) -> list[tuple[str, ...]]:
    # Order-insensitive unless the query orders; floats compared at 9 significant digits.
    def cell(v: object) -> str:
        return f"{v:.9g}" if isinstance(v, float) else repr(v)

    return sorted(tuple(cell(v) for v in r) for r in rows)


@pytest.mark.parametrize("sql", CORPUS.values(), ids=CORPUS.keys())
@pytest.mark.parametrize("user", [EXEC, RAM], ids=["exec", "ram"])
async def test_guarded_sql_returns_identical_results(
    executor: QueryExecutor, sql: str, user: UserContext
) -> None:
    guarded = guard(sql, user, max_rows=100_000)
    original = await executor.run(user, sql)
    rewritten = await executor.run(user, guarded.sql)
    assert rewritten.columns == original.columns
    assert normalised(rewritten.rows) == normalised(original.rows)
    assert original.rows, "corpus query should return data"


async def test_autofixed_round_executes_where_the_original_fails(executor: QueryExecutor) -> None:
    sql = "SELECT drug_name, ROUND(AVG(pack_units), 2) AS avg_units FROM sales GROUP BY 1"
    with pytest.raises(QueryFailed) as err:
        await executor.run(RAM, sql)
    # The self-repair loop needs the primary error, not just Postgres's HINT line.
    assert "round(double precision, integer) does not exist" in err.value.message
    assert "HINT" in err.value.message

    result = await executor.run(RAM, guard(sql, RAM, max_rows=100).sql)
    drugs = await executor.run(RAM, "SELECT COUNT(DISTINCT drug_name) FROM sales")
    assert len(result.rows) == drugs.rows[0][0]
