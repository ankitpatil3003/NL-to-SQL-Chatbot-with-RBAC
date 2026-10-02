from app.nl2sql.consensus import Candidate, reconcile
from app.nl2sql.types import ResultTable, SqlDraft
from app.nl2sql.verify import check
from app.sqlguard.guard import GuardedQuery

GQ = GuardedQuery("SELECT 1", frozenset(), False, (), "SELECT 1")


def cand(
    rows: list[list[object]] | None, columns: list[str] | None = None, answerable: bool = True
) -> Candidate:
    draft = SqlDraft(
        answerable=answerable, sql="x", rules_applied=[], assumptions=[], unanswerable_reason=""
    )
    if rows is None:
        return Candidate("sql", 0.0, draft=draft)
    cols = columns or [f"c{i}" for i in range(len(rows[0]) if rows else 1)]
    return Candidate(
        "sql", 0.0, draft=draft, guarded=GQ, table=ResultTable(cols, rows, False, len(rows))
    )


def test_unanimous_majority_and_split() -> None:
    a, b = [["ZENOVAX", 100]], [["ZENOVAX", 90]]
    assert reconcile([cand(a), cand(a), cand(a)]).agreement == "unanimous"
    m = reconcile([cand(b), cand(a), cand(a)])
    assert m.agreement == "majority" and m.chosen == 1 and m.groups == [[1, 2], [0]]
    s = reconcile([cand(a), cand(b), cand([["GEMTARA", 5]])])
    assert s.agreement == "split" and s.chosen == 0 and len(s.groups) == 3


def test_agreement_tolerates_rounding_order_and_extra_columns() -> None:
    one = cand([["A", 100.0], ["B", 50.0]])
    other = cand([["B", 50.004, 33.3], ["A", 100.0, 66.7]])  # reordered, rounded, + a share column
    assert reconcile([one, other]).agreement == "unanimous"


def test_failures_and_unanswerable_votes() -> None:
    assert reconcile([cand(None), cand([["A", 1]])]).agreement == "single"
    none = reconcile([cand(None, answerable=False), cand(None, answerable=False), cand(None)])
    assert none.agreement == "none" and none.chosen is None and none.groups == [[0, 1]]


def table(columns: list[str], rows: list[list[object]]) -> ResultTable:
    return ResultTable(columns, rows, False, len(rows))


def test_verify_flags_unfiltered_sales_aggregates_only() -> None:
    t = table(["units"], [[5]])
    assert [i.code for i in check("SELECT SUM(pack_units) AS units FROM sales", t)] == [
        "mixed_sources"
    ]
    ok = "SELECT SUM(pack_units) FROM sales WHERE data_source = 'distributor' AND brand_flag = 1"
    assert check(ok, t) == []
    assert check("SELECT drug_name FROM products", t) == []  # not sales, no aggregate


def test_verify_flags_share_from_one_aggregate_and_empty_results() -> None:
    mixed = (
        "SELECT SUM(CASE WHEN data_source = 'distributor' THEN pack_units END) / SUM(pack_units) AS share "
        "FROM sales WHERE data_source IN ('distributor', 'market_data')"
    )
    assert "share_one_aggregate" in [i.code for i in check(mixed, table(["share"], [[0.4]]))]
    separate = (
        "WITH n AS (SELECT SUM(pack_units) v FROM sales WHERE data_source = 'distributor'), "
        "d AS (SELECT SUM(pack_units) v FROM sales WHERE data_source = 'market_data') "
        "SELECT n.v / d.v AS share FROM n, d"
    )
    assert check(separate, table(["share"], [[0.4]])) == []
    empty = check(
        "SELECT org_name FROM organizations WHERE org_name = 'x'", table(["org_name"], [])
    )
    assert [i.code for i in empty] == ["empty"] and empty[0].for_user == ""


def test_a_total_question_answered_with_a_breakdown_is_flagged() -> None:
    grouped = (
        "SELECT period_mo, SUM(pack_units) FROM sales WHERE data_source = 'distributor' GROUP BY 1"
    )
    two_rows = table(["period_mo", "units"], [["2026-07", 1], ["2026-08", 2]])
    for q in ["What are our total sales?", "How is Zenovax performing this quarter in pack units?"]:
        assert [i.code for i in check(grouped, two_rows, q)] == ["unrequested_breakdown"]
    for q in ["Total sales by territory", "How many accounts per GPO?", "Top 10 accounts by units",
              "ZENOVAX units for the last 6 months"]:  # fmt: skip
        assert check(grouped, two_rows, q) == []
    assert check(grouped, table(["units"], [[3]]), "What are our total sales?") == []
