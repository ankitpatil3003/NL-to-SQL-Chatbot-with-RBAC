"""The NL-to-SQL turn as a LangGraph state graph (CLAUDE.md §4.2, v2):

  understand ─┬─ not a data question ─▶ reply
              └─▶ retrieve ─▶ sql ─┬─ unanswerable ─▶ explain
                                   ├─ attempts spent ─▶ fail
                                   └─ result ────────▶ answer

The state is checkpointed per chat, so a turn can pause for the user and resume later. What must
never be checkpointed travels in the per-run context instead: who the user is (re-resolved from
the database on every request, resume included), the model router, the executor and the trace.
Nodes report progress through the stream writer as the same Events the chat API already streams.
"""

import logging
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer

from app.db.executor import QueryExecutor, QueryFailed
from app.knowledge.base import KnowledgeBase
from app.knowledge.fewshots import SelectedExample, select_examples
from app.knowledge.store import Hit
from app.llm.router import LLMRouter
from app.nl2sql.answer import build_notes, plain_language, result_table, synthesize
from app.nl2sql.entities import Resolution, resolve_mentions
from app.nl2sql.generate import build_context, generate_and_run, redact_wac_sql
from app.nl2sql.types import (
    Event,
    HistoryTurn,
    ResultTable,
    SqlDraft,
    TurnResult,
    Understanding,
)
from app.nl2sql.understand import understand
from app.observability.trace import TurnTrace
from app.rbac.context import UserContext
from app.sqlguard.guard import GuardedQuery

log = logging.getLogger(__name__)

DOC_CHUNKS = 3
EXAMPLES = 4

FAILED = (
    "I couldn't build a working query for that question. Try rephrasing it, or be more "
    "specific about the product, time period or accounts you mean."
)

# Types the checkpointer may rebuild from a stored checkpoint (anything else is refused).
CHECKPOINT_TYPES = [
    ("app.nl2sql.types", name)
    for name in ("HistoryTurn", "Understanding", "Mention", "SqlDraft", "ResultTable", "TurnResult")
] + [
    ("app.knowledge.store", "Hit"),
    ("app.knowledge.fewshots", "SelectedExample"),
    ("app.knowledge.fewshots", "Example"),
    ("app.nl2sql.entities", "Resolution"),
    ("app.sqlguard.guard", "GuardedQuery"),
]


@dataclass(slots=True)
class TurnDeps:
    """Per-run context: never checkpointed."""

    user: UserContext
    trace: TurnTrace
    llm: LLMRouter
    kb: KnowledgeBase
    executor: QueryExecutor
    max_rows: int


class TurnState(TypedDict, total=False):
    question: str
    history: list[HistoryTurn]
    understanding: Understanding
    docs: list[Hit]
    examples: list[SelectedExample]
    resolutions: list[Resolution]
    draft: SqlDraft | None
    guarded: GuardedQuery | None
    table: ResultTable | None
    result: TurnResult | None


def new_turn(question: str, history: list[HistoryTurn]) -> TurnState:
    """A turn's input. A chat's checkpoint thread keeps the previous turn's values, so every
    per-turn key is reset here rather than inherited."""
    return TurnState(
        question=question,
        history=history,
        docs=[],
        examples=[],
        resolutions=[],
        draft=None,
        guarded=None,
        table=None,
        result=None,
    )


Ctx = Runtime[TurnDeps]


def _emit(kind: Literal["stage", "answer_delta"], data: Any) -> None:
    get_stream_writer()(Event(kind, data))


def _finish(result: TurnResult) -> dict[str, Any]:
    _emit("answer_delta", result.answer)
    return {"result": result}


# --- Nodes -----------------------------------------------------------------------------------


async def understand_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps = runtime.context
    _emit("stage", "understanding")
    with deps.trace.stage("understand"):
        intent, routed = await understand(deps.llm, state["question"], state["history"], deps.user)
    deps.trace.add_llm("router", routed)
    deps.trace.detail["understanding"] = intent.model_dump()
    return {"understanding": intent}


async def reply_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    intent = state["understanding"]
    status = {"clarify": "clarification", "out_of_scope": "refused"}.get(intent.intent, "answered")
    runtime.context.trace.status = status
    return _finish(TurnResult(status=status, answer=intent.reply))  # type: ignore[arg-type]


async def retrieve_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps = runtime.context
    standalone = _standalone(state)
    _emit("stage", "retrieving")
    with deps.trace.stage("retrieve"):
        docs = await deps.kb.retriever.search(standalone, "doc", k=DOC_CHUNKS)
        if not deps.user.can_view_wac:
            docs = redact_wac_sql(docs)
        examples = await select_examples(deps.kb.retriever, standalone, deps.user, k=EXAMPLES)
        resolutions = await resolve_mentions(
            state["understanding"].mentions, deps.kb.catalog, deps.executor, deps.user
        )
    deps.trace.detail["retrieval"] = {
        "docs": [{"id": d.item_id, "ranks": d.ranks} for d in docs],
        "examples": [{"id": e.example.id, "ranks": e.ranks} for e in examples],
    }
    deps.trace.detail["entities"] = [r.hint() for r in resolutions]
    return {"docs": docs, "examples": examples, "resolutions": resolutions}


async def sql_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps, intent, history = runtime.context, state["understanding"], state["history"]
    _emit("stage", "writing_sql")
    context = build_context(
        _standalone(state),
        docs=state["docs"],
        examples=state["examples"],
        resolutions=state["resolutions"],
        previous=history[-1] if intent.is_follow_up and history else None,
        volume_instead_of_dollars=intent.asks_for_dollars and not deps.user.can_view_wac,
    )
    with deps.trace.stage("sql"):
        outcome = await generate_and_run(
            deps.llm, deps.kb, deps.executor, deps.user, context, max_rows=deps.max_rows
        )
    for call in outcome.llm_calls:
        deps.trace.add_llm("sql", call)
    deps.trace.detail["sql_attempts"] = [
        {"sql": a.sql, "failed_at": a.failed_at, "error": a.error, "autofixes": a.autofixes}
        for a in outcome.attempts
    ]
    if outcome.attempts:
        deps.trace.sql_generated = outcome.attempts[-1].sql
    if not outcome.succeeded or outcome.result is None or outcome.guarded is None:
        return {"draft": outcome.draft, "guarded": None, "table": None}

    guarded, result = outcome.guarded, outcome.result
    deps.trace.sql_executed = guarded.sql
    total = None
    if (guarded.limit_applied and len(result.rows) >= deps.max_rows) or result.truncated:
        with deps.trace.stage("count"):
            total = await _count(deps, guarded.full_sql)
    table = result_table(result, total)
    deps.trace.row_count = table.row_count
    return {"draft": outcome.draft, "guarded": guarded, "table": table}


async def explain_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps, draft = runtime.context, state["draft"]
    assert draft is not None
    deps.trace.status = "answered"
    # The scope / WAC notes matter most exactly here ("show me the West region" from a Northeast
    # director is often declared unanswerable), so they're carried too.
    notes = build_notes(
        None,
        deps.user,
        asked_for_dollars=state["understanding"].asks_for_dollars,
        resolutions=state["resolutions"],
    )
    answer = draft.unanswerable_reason or "That question can't be answered from this data."
    return _finish(
        TurnResult(
            status="answered", answer=answer, standalone_question=_standalone(state), notes=notes
        )
    )


async def fail_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    trace = runtime.context.trace
    trace.status, trace.error = "error", "SQL attempts exhausted"
    return _finish(
        TurnResult(status="error", answer=FAILED, standalone_question=_standalone(state))
    )


async def answer_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps, table, draft, guarded = runtime.context, state["table"], state["draft"], state["guarded"]
    assert table is not None and draft is not None and guarded is not None
    standalone = _standalone(state)
    notes = build_notes(
        table,
        deps.user,
        asked_for_dollars=state["understanding"].asks_for_dollars,
        resolutions=state["resolutions"],
    )
    _emit("stage", "answering")
    with deps.trace.stage("answer"):
        answered = await synthesize(
            deps.llm, standalone, deps.user, table, assumptions=draft.assumptions, notes=notes
        )
    deps.trace.add_llm("answer", answered)
    deps.trace.status = "answered"
    return _finish(
        TurnResult(
            status="answered",
            answer=plain_language(answered.response.text),
            standalone_question=standalone,
            sql=guarded.sql,
            query=guarded.full_sql,
            table=table,
            assumptions=[plain_language(a) for a in draft.assumptions],
            rules_applied=draft.rules_applied,
            notes=notes,
        )
    )


# --- Routing ---------------------------------------------------------------------------------


def after_understand(state: TurnState) -> str:
    return "retrieve" if state["understanding"].intent == "data_question" else "reply"


def after_sql(state: TurnState) -> str:
    draft = state.get("draft")
    if draft is not None and not draft.answerable:
        return "explain"
    return "answer" if state.get("table") is not None else "fail"


def build_graph(checkpointer: Checkpointer = None) -> CompiledStateGraph[Any, Any, Any, Any]:
    g = StateGraph(TurnState, context_schema=TurnDeps)
    g.add_node("understand", understand_node)
    g.add_node("reply", reply_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("sql", sql_node)
    g.add_node("explain", explain_node)
    g.add_node("fail", fail_node)
    g.add_node("answer", answer_node)
    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", after_understand, ["retrieve", "reply"])
    g.add_edge("retrieve", "sql")
    g.add_conditional_edges("sql", after_sql, ["explain", "answer", "fail"])
    for end in ("reply", "explain", "fail", "answer"):
        g.add_edge(end, END)
    return g.compile(checkpointer=checkpointer)


# --- Helpers ---------------------------------------------------------------------------------


def _standalone(state: TurnState) -> str:
    return state["understanding"].standalone_question or state["question"]


async def _count(deps: TurnDeps, full_sql: str) -> int | None:
    """True size of a capped result. Validated SQL, run as the same user; best effort."""
    try:
        counted = await deps.executor.run(deps.user, f"SELECT count(*) FROM ({full_sql}) AS q")
        return int(counted.rows[0][0])
    except QueryFailed:
        log.warning("row count failed", exc_info=True)
        return None
