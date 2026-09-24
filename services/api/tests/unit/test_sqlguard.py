"""Core SQL guard rules. Adversarial inputs live in test_sqlguard_adversarial.py."""

import pytest
import sqlglot

from app.rbac.context import Role, Scope, UserContext
from app.sqlguard.guard import GuardViolation, Violation, guard


def make_user(role: Role) -> UserContext:
    scope = {
        Role.EXEC: None,
        Role.DIRECTOR: Scope("region", "Northeast"),
        Role.RAM: Scope("territory", "New York Metro"),
    }[role]
    return UserContext(
        user_id="U", email="u@x", full_name="U", role=role, territory=None, region=None,
        scope=scope, can_view_wac=role is Role.EXEC,
    )  # fmt: skip


EXEC, DIRECTOR, RAM = (make_user(r) for r in (Role.EXEC, Role.DIRECTOR, Role.RAM))

# Realistic queries shaped by docs/ (metric_definitions, org_hierarchy, period_offsets, ...).
VALID = {
    "market share (separate CTEs)": """
        WITH nova AS (
            SELECT SUM(s.pack_units * p.unit_conversion_factor) AS eq FROM sales s
            JOIN products p ON s.ndc = p.ndc
            WHERE s.data_source = 'distributor' AND s.brand_flag = 1 AND p.market_subcategory = 'Docetaxel'),
        mkt AS (
            SELECT SUM(s.pack_units * p.unit_conversion_factor) AS eq FROM sales s
            JOIN products p ON s.ndc = p.ndc
            WHERE s.data_source = 'market_data' AND p.market_subcategory = 'Docetaxel')
        SELECT nova.eq / NULLIF(mkt.eq, 0) AS market_share FROM nova, mkt""",
    "grandparent roll-up": """
        SELECT COALESCE(o.grandparent_org_name, o.org_name) AS account, SUM(s.pack_units) AS units
        FROM sales s JOIN organizations o ON s.org_id = o.org_id
        WHERE s.data_source = 'distributor' AND s.brand_flag = 1 AND s.mo_offset IN (1, 2, 3)
        GROUP BY 1 ORDER BY units DESC LIMIT 10""",
    "territory via zip": """
        SELECT z.territory_name, SUM(s.pack_units) FROM sales s
        JOIN organizations o ON o.org_id = s.org_id JOIN zip_territory z ON z.zip = o.zip
        GROUP BY z.territory_name""",
    "monthly trend + window": """
        SELECT period_mo, SUM(pack_units) AS units,
               SUM(pack_units) - LAG(SUM(pack_units)) OVER (ORDER BY period_mo) AS change
        FROM sales WHERE data_source = 'distributor' AND mo_offset BETWEEN 0 AND 5
        GROUP BY period_mo ORDER BY period_mo""",
    "R3M vs R6M with CASE": """
        SELECT drug_name,
               SUM(CASE WHEN mo_offset IN (0, 1, 2) THEN pack_units END) AS r3m,
               SUM(CASE WHEN mo_offset IN (3, 4, 5) THEN pack_units END) AS r6m
        FROM sales WHERE data_source = 'distributor' AND brand_flag = 1 GROUP BY drug_name""",
    "340B share with casts": """
        SELECT ROUND(100.0 * SUM(CASE WHEN o.is_340b = 1 THEN s.pack_units ELSE 0 END)::numeric
               / NULLIF(SUM(s.pack_units), 0), 2) AS pct_340b
        FROM sales s JOIN organizations o USING (org_id) WHERE s.data_source = 'distributor'""",
    "union + string/date functions": """
        SELECT UPPER(drug_name) AS d, TO_CHAR(TO_DATE(transaction_date, 'YYYY-MM-DD'), 'YYYY-MM') AS m
        FROM sales WHERE brand_flag = 1
        UNION ALL
        SELECT generic_name, SPLIT_PART(ndc, '-', 1) FROM products""",
    "fuzzy name match": """
        SELECT org_name FROM organizations WHERE similarity(org_name, 'memorial health') > 0.3
        ORDER BY similarity(org_name, 'memorial health') DESC LIMIT 5""",
}


@pytest.mark.parametrize("sql", VALID.values(), ids=VALID.keys())
@pytest.mark.parametrize("user", [EXEC, DIRECTOR, RAM], ids=["exec", "director", "ram"])
def test_valid_analytics_queries_pass(sql: str, user: UserContext) -> None:
    result = guard(sql, user, max_rows=1000)
    sqlglot.parse_one(result.sql, read="postgres")  # output is itself valid SQL
    assert result.tables <= {"sales", "organizations", "products", "zip_territory"}


def test_reports_base_tables_but_not_cte_names() -> None:
    result = guard(VALID["market share (separate CTEs)"], RAM, max_rows=1000)
    assert result.tables == {"sales", "products"}


def test_exec_may_use_wac_and_others_may_not() -> None:
    sql = (
        "SELECT SUM(wac) AS revenue FROM sales WHERE data_source = 'distributor' AND brand_flag = 1"
    )
    assert guard(sql, EXEC, max_rows=1000).tables == {"sales"}
    for user in (DIRECTOR, RAM):
        with pytest.raises(GuardViolation) as err:
            guard(sql, user, max_rows=1000)
        assert err.value.code is Violation.WAC_NOT_PERMITTED
        assert "pack_units" in err.value.message  # tells the model what to do instead


# --- LIMIT ---------------------------------------------------------------------------------------


def limit_of(sql: str) -> str | None:
    node = sqlglot.parse_one(sql, read="postgres").args.get("limit")
    return node.sql(dialect="postgres") if node else None


def test_adds_limit_when_missing() -> None:
    result = guard("SELECT org_id FROM organizations", RAM, max_rows=500)
    assert result.limit_applied and limit_of(result.sql) == "LIMIT 500"


def test_lowers_excessive_limit() -> None:
    result = guard("SELECT org_id FROM organizations LIMIT 100000", RAM, max_rows=500)
    assert result.limit_applied and limit_of(result.sql) == "LIMIT 500"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT org_id FROM organizations LIMIT 5",
        "SELECT org_id FROM organizations FETCH FIRST 5 ROWS ONLY",
    ],
)
def test_keeps_small_limits_including_fetch_first(sql: str) -> None:
    result = guard(sql, RAM, max_rows=500)
    assert not result.limit_applied
    assert "5" in (limit_of(result.sql) or "")


def test_limit_applies_to_whole_union() -> None:
    result = guard("SELECT ndc FROM products UNION SELECT ndc FROM sales", RAM, max_rows=50)
    assert result.sql.rstrip().endswith("LIMIT 50")


# --- Domain rules --------------------------------------------------------------------------------


@pytest.mark.parametrize("expr", ["CURRENT_DATE", "NOW()", "CURRENT_TIMESTAMP"])
def test_wall_clock_time_is_rejected_with_offset_guidance(expr: str) -> None:
    with pytest.raises(GuardViolation) as err:
        guard(
            f"SELECT COUNT(*) FROM sales WHERE transaction_date > {expr} - INTERVAL '30 days'",
            EXEC,
            max_rows=10,
        )
    assert err.value.code is Violation.WALL_CLOCK_TIME
    assert "mo_offset" in err.value.message


# --- Structural rejections -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("SELEC * FRM sales", Violation.NOT_A_QUERY),
        ("", Violation.SYNTAX),
        ("SELECT 1; SELECT 2", Violation.MULTIPLE_STATEMENTS),
        ("DELETE FROM sales", Violation.NOT_A_QUERY),
        ("VALUES (1)", Violation.NOT_A_QUERY),
        ("SELECT * FROM users", Violation.FORBIDDEN_TABLE),
        ("SELECT * FROM public.sales", Violation.SCHEMA_QUALIFIED),
        ("SELECT * FROM generate_series(1, 3)", Violation.TABLE_FUNCTION),
        ("SELECT pg_sleep(1)", Violation.FORBIDDEN_FUNCTION),
    ],
)
def test_structural_rejections(sql: str, code: Violation) -> None:
    with pytest.raises(GuardViolation) as err:
        guard(sql, EXEC, max_rows=10)
    assert err.value.code is code
