"""SQL guard (CLAUDE.md §5, layer L3): validate and normalise LLM-written SQL before execution.

Not the security boundary; the database is (app/db/executor.py, db/20_rbac.sql). The guard's job:
  * reject anything that isn't a single read-only query, early and cheaply;
  * turn violations into precise, actionable messages the model can fix in a self-repair turn;
  * encode domain rules the database can't (e.g. relative time must use the offset columns);
  * cap result size with a LIMIT.

We execute exactly what we validated: the returned SQL is sqlglot's regeneration of the checked
tree, never the original text. Otherwise any sqlglot-vs-Postgres parser disagreement would become
a bypass.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.rbac.context import UserContext

# sqlglot logs a warning whenever it falls back to an opaque Command; we reject those anyway.
logging.getLogger("sqlglot").setLevel(logging.ERROR)

DIALECT = "postgres"

ALLOWED_TABLES = frozenset({"sales", "organizations", "products", "zip_territory"})

# Postgres functions sqlglot doesn't model get parsed as exp.Anonymous; every dangerous function
# (pg_sleep, set_config, dblink, pg_read_file, lo_*, rbac.*, ...) lands there. So Anonymous calls
# must be on this list, while typed sqlglot functions (standard SQL: SUM, ROUND, COALESCE,
# DATE_TRUNC, window functions, ...) are allowed.
ALLOWED_ANONYMOUS_FUNCTIONS = frozenset(
    {
        "btrim", "date_part", "initcap", "left", "lpad", "ltrim", "right", "rpad", "rtrim",
        "strpos", "to_number", "similarity", "word_similarity", "width_bucket", "bool_or",
        "bool_and", "every", "mode", "trunc", "sign", "div", "mod", "cbrt", "ceiling", "floor",
    }
)  # fmt: skip

# Nodes that write, change state or escape the query model, wherever they appear (incl. CTEs).
FORBIDDEN_NODES: tuple[type[exp.Expr], ...] = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter,
    exp.TruncateTable, exp.Command, exp.Copy, exp.Set, exp.Transaction, exp.Commit,
    exp.Rollback, exp.Grant, exp.Use, exp.LoadData, exp.Pragma,
)  # fmt: skip

# The data is anchored to its refresh date via wk_offset/mo_offset (docs/period_offsets.md).
WALL_CLOCK_NODES: tuple[type[exp.Expr], ...] = (
    exp.CurrentDate, exp.CurrentTimestamp, exp.CurrentTime, exp.CurrentDatetime,
)  # fmt: skip


class Violation(StrEnum):
    SYNTAX = "syntax"
    MULTIPLE_STATEMENTS = "multiple_statements"
    NOT_A_QUERY = "not_a_query"
    WRITE_OPERATION = "write_operation"
    FORBIDDEN_TABLE = "forbidden_table"
    SCHEMA_QUALIFIED = "schema_qualified"
    TABLE_FUNCTION = "table_function"
    FORBIDDEN_FUNCTION = "forbidden_function"
    WAC_NOT_PERMITTED = "wac_not_permitted"
    WALL_CLOCK_TIME = "wall_clock_time"


class GuardViolation(Exception):
    """`message` is written for the model: what is wrong and how to fix it."""

    def __init__(self, code: Violation, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class GuardedQuery:
    sql: str  # the normalised SQL to execute
    tables: frozenset[str]  # base tables referenced
    limit_applied: bool  # the guard added or lowered the LIMIT


def guard(sql: str, user: UserContext, *, max_rows: int) -> GuardedQuery:
    root = _parse_single(sql)
    _check_is_read_only_query(root)
    tables = _check_tables(root)
    _check_functions(root)
    if not user.can_view_wac:
        _check_no_wac(root)
    _check_no_wall_clock(root)
    limit_applied = _enforce_limit(root, max_rows)
    return GuardedQuery(root.sql(dialect=DIALECT), frozenset(tables), limit_applied)


def _parse_single(sql: str) -> exp.Expr:
    try:
        statements = [s for s in sqlglot.parse(sql, read=DIALECT) if s is not None]
    except ParseError as exc:
        first = exc.errors[0]["description"] if exc.errors else str(exc)
        raise GuardViolation(Violation.SYNTAX, f"SQL could not be parsed: {first}") from None
    if not statements:
        raise GuardViolation(Violation.SYNTAX, "No SQL statement found.")
    if len(statements) > 1:
        raise GuardViolation(
            Violation.MULTIPLE_STATEMENTS,
            "Exactly one statement is allowed. Combine the logic with CTEs (WITH ...) instead.",
        )
    return statements[0]


def _check_is_read_only_query(root: exp.Expr) -> None:
    if not isinstance(root, exp.Select | exp.SetOperation):
        raise GuardViolation(
            Violation.NOT_A_QUERY, "Only a single SELECT query (optionally with CTEs) is allowed."
        )
    for node in root.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise GuardViolation(
                Violation.WRITE_OPERATION,
                f"{node.key.upper()} is not allowed: the assistant has read-only access.",
            )
        if isinstance(node, exp.Select) and node.args.get("into"):
            raise GuardViolation(Violation.WRITE_OPERATION, "SELECT ... INTO is not allowed.")
        if isinstance(node, exp.Lock):
            raise GuardViolation(
                Violation.WRITE_OPERATION, "Row locking (FOR UPDATE/SHARE) is not allowed."
            )


def _check_tables(root: exp.Expr) -> set[str]:
    cte_names = {cte.alias_or_name.lower() for cte in root.find_all(exp.CTE)}
    used: set[str] = set()
    allowed = ", ".join(sorted(ALLOWED_TABLES))
    for table in root.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            raise GuardViolation(
                Violation.TABLE_FUNCTION,
                f"Functions in FROM are not allowed. Query only these tables: {allowed}.",
            )
        name = table.name.lower()
        if table.args.get("db") or table.args.get("catalog"):
            raise GuardViolation(
                Violation.SCHEMA_QUALIFIED,
                f"Use unqualified table names ({allowed}); '{table.sql(dialect=DIALECT)}' is "
                "schema-qualified.",
            )
        if name in cte_names:
            continue
        if name not in ALLOWED_TABLES:
            raise GuardViolation(
                Violation.FORBIDDEN_TABLE, f"Table '{name}' is not available. Use only: {allowed}."
            )
        used.add(name)
    return used


def _check_functions(root: exp.Expr) -> None:
    for func in root.find_all(exp.Anonymous):
        name = func.name.lower()
        qualified = isinstance(func.parent, exp.Dot)
        if qualified or name not in ALLOWED_ANONYMOUS_FUNCTIONS:
            raise GuardViolation(
                Violation.FORBIDDEN_FUNCTION,
                f"Function '{name}' is not allowed. Use standard SQL functions (aggregates, "
                "arithmetic, COALESCE/NULLIF, CASE, string and date functions, window functions).",
            )


def _check_no_wac(root: exp.Expr) -> None:
    # Any identifier, not just columns: aliases, USING (...), quoted forms. The scoped views don't
    # have the column at all; this turns a database error into a clear instruction.
    for ident in root.find_all(exp.Identifier):
        if ident.name.lower() == "wac":
            raise GuardViolation(
                Violation.WAC_NOT_PERMITTED,
                "This user may not see WAC (dollar/pricing) data. Do not reference `wac`; "
                "answer in volume instead: pack_units, or equivalents "
                "(pack_units * products.unit_conversion_factor).",
            )


def _check_no_wall_clock(root: exp.Expr) -> None:
    if any(True for _ in root.find_all(*WALL_CLOCK_NODES)):
        raise GuardViolation(
            Violation.WALL_CLOCK_TIME,
            "Do not use CURRENT_DATE/NOW(): data is relative to its refresh date. Use the offset "
            "columns: mo_offset (0 = current month, 1 = last month), wk_offset (0 = current "
            "week), or the period_mo / period_qtr labels.",
        )


def _enforce_limit(root: exp.Expr, max_rows: int) -> bool:
    assert isinstance(root, exp.Select | exp.SetOperation)
    current = root.args.get("limit")
    # LIMIT n and FETCH FIRST n ROWS both live in the "limit" arg; keep a literal n <= max_rows
    # (replacing "FETCH FIRST 5" with LIMIT max_rows would silently turn a top-5 into a top-1000).
    if isinstance(current, exp.Limit):
        value = current.expression
    elif isinstance(current, exp.Fetch):
        value = current.args.get("count")
    else:
        value = None
    if isinstance(value, exp.Literal) and value.is_int and int(value.this) <= max_rows:
        return False
    root.limit(max_rows, copy=False)
    return True
