from decimal import Decimal

from evals.compare import compare, value_matches


def test_numbers_match_within_rounding_tolerance() -> None:
    assert value_matches(Decimal("13.1"), 13.14)  # 1-decimal rounding of a percentage
    assert value_matches(449239.0, 449239)
    assert value_matches(1_000_000, 1_004_000)  # 0.4% relative
    assert not value_matches(13.1, 0.131)  # percent vs fraction is a real difference
    assert not value_matches(100, 110)


def test_strings_are_case_insensitive_and_columns_are_ignored() -> None:
    ok, _ = compare([["ZENOVAX", 10]], [[10, "Zenovax", 0.5]])  # reordered + extra column
    assert ok


def test_ordered_comparison_catches_wrong_ranking() -> None:
    ref = [["A", 3], ["B", 2]]
    assert compare(ref, [["A", 3], ["B", 2]], ordered=True)[0]
    assert not compare(ref, [["B", 2], ["A", 3]], ordered=True)[0]
    assert compare(ref, [["B", 2], ["A", 3]], ordered=False)[0]


def test_row_counts_and_extra_rows() -> None:
    ref = [["2026-Q3", 5]]
    act = [["2026-Q2", 4], ["2026-Q3", 5]]
    assert not compare(ref, act)[0]
    assert compare(ref, act, extra_rows_ok=True)[0]
    assert not compare(ref, [], extra_rows_ok=True)[0]


def _result(status="answered", rows=None, sql="SELECT 1", notes=()):  # type: ignore[no-untyped-def]
    from types import SimpleNamespace

    table = None if rows is None else SimpleNamespace(columns=["a", "b"], rows=rows)
    return SimpleNamespace(status=status, table=table, sql=sql, notes=list(notes))


def test_score_status_in_allows_several_safe_outcomes() -> None:
    from evals.run import score

    case = {"status_in": ["refused", "answered"]}
    assert score(case, _result("refused"), None)[0]
    assert score(case, _result("answered", rows=[]), None)[0]
    assert not score(case, _result("error"), None)[0]


def test_score_must_not_contain_checks_cells_not_answer_text() -> None:
    from evals.run import score

    case = {"must_not_contain": ["Texas"]}
    assert score(case, _result(rows=[["New York Metro", 10]]), None)[0]
    ok, why = score(case, _result(rows=[["Texas", 10]]), None)
    assert not ok and "Texas" in why


def test_score_sql_must_not_contain_matches_whole_words() -> None:
    from evals.run import score

    case = {"sql_must_not_contain": ["wac"]}
    assert score(case, _result(sql="SELECT SUM(pack_units) FROM sales"), None)[0]
    assert not score(case, _result(sql="SELECT SUM(wac) FROM sales"), None)[0]


def test_score_reference_only_applies_to_answered_turns() -> None:
    from evals.run import score

    case = {"status_in": ["refused", "answered"]}
    assert score(case, _result("refused"), [[1]])[0]  # refusing a disallowed request is fine
    assert not score(case, _result("answered", rows=[[2]]), [[1]])[0]
