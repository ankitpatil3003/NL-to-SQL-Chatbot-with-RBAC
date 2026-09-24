"""The contract's SQL templates are executable documentation: each must pass the guard and
return data on the full dataset, for a scoped user and for an exec."""

from collections.abc import AsyncIterator

import pytest

from app.core.config import Settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor
from app.knowledge.contract import load_catalog, load_contract
from app.rbac.context import UserContext
from app.sqlguard.guard import guard

from ..unit.test_sqlguard import EXEC, RAM

TEMPLATES = [r for r in load_contract().rules if r.sql]


@pytest.fixture
async def executor(settings: Settings) -> AsyncIterator[QueryExecutor]:
    ex = QueryExecutor(settings)
    yield ex
    await ex.dispose()


@pytest.mark.parametrize("rule", TEMPLATES, ids=lambda r: r.id)
@pytest.mark.parametrize("user", [EXEC, RAM], ids=["exec", "ram"])
async def test_contract_sql_templates_execute(
    executor: QueryExecutor, rule, user: UserContext
) -> None:  # type: ignore[no-untyped-def]
    result = await executor.run(user, guard(rule.sql, user, max_rows=1000).sql)
    assert result.rows and result.rows[0][-1] is not None


async def test_market_share_template_matches_the_documented_formula(
    executor: QueryExecutor,
) -> None:
    """MS-1 follows docs/metric_definitions.md exactly. On this data that exceeds 100% for
    ZENOVAX (market_data has no NovaPharma rows; see MS-3), so assert the formula, not a range."""
    rule = load_contract().rule("MS-1")
    share = (await executor.run(EXEC, guard(rule.sql, EXEC, max_rows=10).sql)).rows[0][0]
    nova = await executor.run(
        EXEC,
        "SELECT SUM(s.pack_units * p.unit_conversion_factor) FROM sales s JOIN products p ON s.ndc = p.ndc "
        "WHERE s.data_source = 'distributor' AND s.brand_flag = 1 AND p.market_subcategory = 'Docetaxel' "
        "AND s.mo_offset IN (0, 1, 2)",
    )
    market = await executor.run(
        EXEC,
        "SELECT SUM(s.pack_units * p.unit_conversion_factor) FROM sales s JOIN products p ON s.ndc = p.ndc "
        "WHERE s.data_source = 'market_data' AND p.market_subcategory = 'Docetaxel' AND s.mo_offset IN (0, 1, 2)",
    )
    assert float(share) == pytest.approx(100 * nova.rows[0][0] / market.rows[0][0], abs=0.05)


async def test_catalog_matches_reference_data(settings: Settings) -> None:
    engine = build_engine(settings)
    try:
        catalog = await load_catalog(engine)
    finally:
        await engine.dispose()
    nova = {p[0] for p in catalog.products if p[1] == 1}
    assert nova == {
        "ZENOVAX",
        "CARBOTREL",
        "GEMTARA",
        "PAXELIUM",
        "ONCOSETRON",
        "CYCLONOVA",
        "LUPREX DEPOT",
    }
    assert len(catalog.territories) == 15
    assert {"Onmark", "ION", "Unity", "VitalSource"} <= set(catalog.gpos)
