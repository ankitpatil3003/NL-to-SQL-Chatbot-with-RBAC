"""Deterministic checks on the chosen query and its result: the business-rule mistakes that change
numbers without causing an error. Each issue is written for the model, so it can repair the query;
an issue that survives the repair is shown to the user as a caveat."""

from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from app.nl2sql.types import ResultTable
from app.sqlguard.guard import DIALECT


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    for_model: str  # what is wrong and how to fix it (repair round)
    for_user: str  # the caveat shown if it survives the repair ("" = nothing to say)


def check(sql: str, table: ResultTable) -> list[Issue]:
    issues: list[Issue] = []
    try:
        root = sqlglot.parse_one(sql, read=DIALECT)
    except sqlglot.errors.ParseError:
        return issues  # it ran, so Postgres parsed it; nothing more to say here
    columns = {c.name.lower() for c in root.find_all(exp.Column)}
    tables = {t.name.lower() for t in root.find_all(exp.Table)}

    if "sales" in tables and "data_source" not in columns and _aggregates(root):
        issues.append(
            Issue(
                "mixed_sources",
                "The query aggregates sales without filtering data_source, so it mixes paid "
                "demand, free drug (hub_dispense) and third-party market rows. Sales means paid "
                "demand (DS-1) unless the question explicitly asks for free drug or the market.",
                "These figures combine paid demand, free drug and third-party market volume.",
            )
        )
    if any("share" in c.lower() for c in table.columns) and _mixes_sources(root):
        issues.append(
            Issue(
                "share_one_aggregate",
                "Market share mixes data sources inside one aggregate. Compute the NovaPharma "
                "numerator (distributor) and the market denominator (market_data) in separate "
                "CTEs, then divide (MS-1).",
                "This market share wasn't computed with the standard method; verify before use.",
            )
        )
    if table.row_count == 0:
        issues.append(
            Issue(
                "empty",
                "The query returned no rows. Check every filter value against the names "
                "resolved from the data and the time window; if no data truly matches, keep the "
                "query.",
                "",  # the answer itself says nothing matched
            )
        )
    return issues


def _aggregates(root: exp.Expr) -> bool:
    return any(True for _ in root.find_all(exp.Sum, exp.Count, exp.Avg))


def _mixes_sources(root: exp.Expr) -> bool:
    """One SELECT whose own filter admits both distributor and market_data rows."""
    for select in root.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue
        values = {
            lit.this
            for pred in where.find_all(exp.EQ, exp.In)
            if any(c.name.lower() == "data_source" for c in pred.find_all(exp.Column))
            for lit in pred.find_all(exp.Literal)
            if lit.is_string
        }
        if {"distributor", "market_data"} <= values:
            return True
    return False
