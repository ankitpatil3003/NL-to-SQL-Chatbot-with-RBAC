"""Stage 4, SQL generation with guard, execution and self-repair.

The model writes SQL from: the semantic contract (cached system block), the user's scope, the
retrieved doc chunks and examples, resolved entity names and, for follow-ups, the previous SQL.
The SQL guard validates it and the scoped executor runs it. On a guard violation or database
error the exact message goes back to the model as a follow-up turn (up to MAX_REPAIRS times):
execution feedback is the cheapest accuracy boost available.
"""

import re
from dataclasses import dataclass, field, replace
from typing import Literal

from app.db.executor import QueryExecutor, QueryFailed, QueryResult
from app.knowledge.base import KnowledgeBase
from app.knowledge.contract import render_contract, render_user_scope
from app.knowledge.fewshots import SelectedExample
from app.knowledge.store import Hit
from app.llm.base import LLMRequest, Message, SystemBlock
from app.llm.router import LLMRouter, RoutedResponse
from app.nl2sql.entities import Resolution
from app.nl2sql.prompts import prompt
from app.nl2sql.types import HistoryTurn, SqlDraft
from app.rbac.context import UserContext
from app.sqlguard.guard import GuardedQuery, GuardViolation, guard

MAX_REPAIRS = 2

# SQL that uses the wac column: SUM(wac), s.wac, wac) ... Doc chunks are retrieved by similarity
# and not role-aware (examples are filtered separately), so for users without WAC access these
# lines are redacted: the model shouldn't be shown a pattern it isn't allowed to use. Prose about
# WAC (e.g. "only Execs may see it") stays.
WAC_SQL = re.compile(r"(\(\s*|\.)wac\b|\bwac\s*\)|\bwac\s*[<>=]", re.IGNORECASE)
WAC_REDACTED = "[pricing formula omitted: not available at this user's access level]"


def redact_wac_sql(docs: list[Hit]) -> list[Hit]:
    def clean(text: str) -> str:
        lines = text.splitlines()
        return "\n".join(WAC_REDACTED if WAC_SQL.search(line) else line for line in lines)

    return [replace(d, content=clean(d.content)) for d in docs]


@dataclass(slots=True)
class SqlAttempt:
    sql: str
    error: str | None = None
    failed_at: Literal["guard", "database"] | None = None
    autofixes: tuple[str, ...] = ()


@dataclass(slots=True)
class SqlOutcome:
    draft: SqlDraft | None = None
    guarded: GuardedQuery | None = None
    result: QueryResult | None = None
    attempts: list[SqlAttempt] = field(default_factory=list)
    llm_calls: list[RoutedResponse] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.result is not None

    @property
    def unanswerable(self) -> bool:
        return self.draft is not None and not self.draft.answerable


def build_context(
    question: str,
    *,
    docs: list[Hit],
    examples: list[SelectedExample],
    resolutions: list[Resolution],
    previous: HistoryTurn | None,
    volume_instead_of_dollars: bool = False,
) -> str:
    parts: list[str] = []
    if docs:
        parts.append("## Relevant documentation")
        parts += [f"### {d.title}\n{d.content}" for d in docs]
    if examples:
        parts.append("## Worked examples (similar questions; adapt, don't copy blindly)")
        parts += [
            f"Q: {s.example.question}\n```sql\n{s.example.sql.strip()}\n```" for s in examples
        ]
    if resolutions:
        parts.append("## Names resolved against the data (use these exact values)")
        parts += [r.hint() for r in resolutions]
    if previous is not None and previous.sql:
        parts.append(
            "## Previous question and its SQL (the new question refines it; keep its filters "
            "and window unless told otherwise)"
        )
        parts.append(f"Q: {previous.question}\n```sql\n{previous.sql}\n```")
    if volume_instead_of_dollars:
        # docs/security_model.md: offer volume instead of refusing. Measured: without this, a
        # model marked "total sales in dollars" from a RAM as unanswerable (eval 20260924-173557).
        parts.append(
            "## Access note\nThe user asked for dollar figures, which they may not see (SEC-1). "
            "Answer the same question in volume (pack_units) instead. Do not mark it unanswerable."
        )
    parts.append(f"## Question\n{question}")
    return "\n\n".join(parts)


def sql_system_blocks(kb: KnowledgeBase, user: UserContext) -> list[SystemBlock]:
    return [
        SystemBlock(f"{prompt('sql')}\n\n{render_contract(kb.contract, kb.catalog)}", cache=True),
        SystemBlock(render_user_scope(user)),
    ]


async def generate_and_run(
    llm: LLMRouter,
    kb: KnowledgeBase,
    executor: QueryExecutor,
    user: UserContext,
    context: str,
    *,
    max_rows: int,
) -> SqlOutcome:
    outcome = SqlOutcome()
    system = sql_system_blocks(kb, user)
    messages = [Message("user", context)]

    for _ in range(MAX_REPAIRS + 1):
        routed = await llm.complete(
            LLMRequest(
                task="sql", system=system, messages=messages, max_tokens=4000, output=SqlDraft
            )
        )
        outcome.llm_calls.append(routed)
        draft = routed.response.data
        assert isinstance(draft, SqlDraft)
        outcome.draft = draft
        if not draft.answerable:
            return outcome

        attempt = SqlAttempt(sql=draft.sql)
        outcome.attempts.append(attempt)
        try:
            guarded = guard(draft.sql, user, max_rows=max_rows)
            attempt.autofixes = guarded.autofixes
            outcome.guarded = guarded
            outcome.result = await executor.run(user, guarded.sql)
            return outcome
        except GuardViolation as exc:
            attempt.failed_at, attempt.error = "guard", exc.message
        except QueryFailed as exc:
            attempt.failed_at, attempt.error = "database", exc.message

        messages += [
            Message("assistant", routed.response.text),
            Message(
                "user",
                f"That query was rejected by the {attempt.failed_at}: {attempt.error}\n"
                "Fix the problem and return the corrected JSON.",
            ),
        ]
    return outcome
