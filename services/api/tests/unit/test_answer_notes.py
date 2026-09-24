from app.nl2sql.answer import build_notes, render_table
from app.nl2sql.entities import Resolution
from app.nl2sql.types import ResultTable

from .test_sqlguard import EXEC, RAM


def table(columns: list[str], rows: list[list[object]], truncated: bool = False) -> ResultTable:
    return ResultTable(columns=columns, rows=rows, truncated=truncated, row_count=len(rows))


def test_dollar_note_only_for_users_without_wac() -> None:
    t = table(["total_units"], [[10]])
    assert any("WAC" in n for n in build_notes(t, RAM, asked_for_dollars=True, resolutions=[]))
    assert build_notes(t, EXEC, asked_for_dollars=True, resolutions=[]) == []
    assert build_notes(t, RAM, asked_for_dollars=False, resolutions=[]) == []


def test_out_of_scope_mentions_are_explained() -> None:
    texas = Resolution(
        "Texas", "territory", "zip_territory.territory_name", ("Texas",), 1.0, outside_scope=True
    )
    notes = build_notes(None, RAM, asked_for_dollars=False, resolutions=[texas])
    assert notes and "Texas" in notes[0] and "New York Metro" in notes[0]


def test_market_share_over_100_is_explained_ms3() -> None:
    over = table(["territory_name", "market_share_pct"], [["Texas", 112.4], ["Mountain", 91.0]])
    under = table(["territory_name", "market_share_pct"], [["Mountain", 91.0]])
    assert any(
        "above 100%" in n for n in build_notes(over, EXEC, asked_for_dollars=False, resolutions=[])
    )
    assert build_notes(under, EXEC, asked_for_dollars=False, resolutions=[]) == []


def test_render_table_caps_rows_for_the_prompt() -> None:
    rendered = render_table(table(["n"], [[i] for i in range(50)]))
    assert "| 29 |" in rendered and "| 30 |" not in rendered and "(50 rows in total)" in rendered
    assert render_table(table(["n"], [])) == "(no rows)"


def test_wac_sql_lines_are_redacted_but_prose_is_kept() -> None:
    from app.knowledge.store import Hit
    from app.nl2sql.generate import WAC_REDACTED, redact_wac_sql

    doc = Hit(
        "doc:x#0",
        "Revenue",
        "Gross Revenue = SUM(wac) WHERE ...\nOnly Execs can see WAC values.\nSELECT s.wac FROM sales s\nORDER BY wac DESC",
        None,
        1.0,
    )
    cleaned = redact_wac_sql([doc])[0].content.splitlines()
    assert cleaned == [
        WAC_REDACTED,
        "Only Execs can see WAC values.",
        WAC_REDACTED,
        "ORDER BY wac DESC",
    ]
