"""Stage 5, answer synthesis: turn the query result into a short natural-language answer.

The notes the user must see (dollars unavailable, out-of-scope requests, market share above 100%)
are computed deterministically here and passed to the model as facts, not left to it to notice.
"""

import datetime as dt
import re
from decimal import Decimal
from typing import Any

from app.db.executor import QueryResult
from app.llm.base import LLMRequest, Message, SystemBlock
from app.llm.router import LLMRouter, RoutedResponse
from app.nl2sql.entities import Resolution
from app.nl2sql.prompts import prompt
from app.nl2sql.types import ResultTable
from app.rbac.context import UserContext

# Raw column names models still leak into prose despite the prompt (Nemotron wrote "37,021
# pack_units" after being told not to). A rule that must hold is enforced in code.
COLUMN_WORDS = {
    "pack_units": "units",
    "total_mg": "mg",
    "period_mo": "month",
    "period_qtr": "quarter",
}
_COLUMN_RE = re.compile(r"\b(" + "|".join(COLUMN_WORDS) + r")\b")


def plain_language(text: str) -> str:
    return _COLUMN_RE.sub(lambda m: COLUMN_WORDS[m.group(1)], text)


PROMPT_ROWS = 30  # rows shown to the answer model; the UI shows the full table
UI_ROWS = 500


def jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dt.date | dt.datetime):
        return value.isoformat()
    return value


def result_table(result: QueryResult) -> ResultTable:
    rows = [[jsonable(v) for v in row] for row in result.rows[:UI_ROWS]]
    return ResultTable(
        columns=result.columns,
        rows=rows,
        truncated=result.truncated or len(result.rows) > UI_ROWS,
        row_count=len(result.rows),
    )


def build_notes(
    table: ResultTable | None,
    user: UserContext,
    *,
    asked_for_dollars: bool,
    resolutions: list[Resolution],
) -> list[str]:
    notes: list[str] = []
    if asked_for_dollars and not user.can_view_wac:
        notes.append(
            "Dollar (WAC) figures aren't available at your access level, so this answer uses "
            "unit volume instead."
        )
    for r in resolutions:
        if r.outside_scope:
            notes.append(
                f'"{r.mention}" is outside your data scope ({user.scope_label}); the results '
                "cover only what you can access."
            )
    if table is not None:
        share_cols = [i for i, c in enumerate(table.columns) if "share" in c.lower()]
        over_100 = any(
            isinstance(row[i], int | float) and row[i] > 100
            for row in table.rows
            for i in share_cols
        )
        if over_100:
            notes.append(
                "Market share above 100%: in this dataset the third-party market data excludes "
                "NovaPharma's own volume, so the documented formula compares our volume with "
                "competitor volume rather than giving a true share."
            )
        if table.truncated:
            notes.append(f"Only the first {len(table.rows)} rows are shown.")
    return notes


def render_table(table: ResultTable) -> str:
    if not table.rows:
        return "(no rows)"
    head = "| " + " | ".join(table.columns) + " |\n|" + "---|" * len(table.columns)
    body = "\n".join(
        "| " + " | ".join("" if v is None else str(v) for v in row) + " |"
        for row in table.rows[:PROMPT_ROWS]
    )
    more = f"\n({table.row_count} rows in total)" if table.row_count > PROMPT_ROWS else ""
    return f"{head}\n{body}{more}"


async def synthesize(
    llm: LLMRouter,
    question: str,
    user: UserContext,
    table: ResultTable,
    *,
    assumptions: list[str],
    notes: list[str],
) -> RoutedResponse:
    parts = [
        f"Question: {question}",
        f"User: {user.full_name}, {user.role.value}, scope: {user.scope_label}",
    ]
    if assumptions:
        parts.append("Assumptions: " + "; ".join(assumptions))
    if notes:
        parts.append("Notes to state: " + " ".join(notes))
    parts.append(f"Query result:\n{render_table(table)}")
    return await llm.complete(
        LLMRequest(
            task="answer",
            system=[SystemBlock(prompt("answer"), cache=True)],
            messages=[Message("user", "\n\n".join(parts))],
            max_tokens=1500,
            temperature=0.2,
        )
    )
