"""The NL-to-SQL turn as a LangGraph state graph (CLAUDE.md §4.2, v2):

  understand ─┬─ not a data question ─▶ reply
              └─▶ retrieve ─▶ plan ─▶ review ─┬─ feedback ─▶ plan (revise)
                                              └─▶ sql (N candidates) ─▶ reconcile ─┐
        ┌─────────────────────────────────────────────────────────────────────────┘
        ├─ unanswerable ─▶ explain
        ├─ none ran ─────▶ fail
        └─▶ verify ─▶ answer

Accuracy first. `sql` generates several candidates (different sampling and model family) and
runs them; `reconcile` keeps the result most of them agree on; `verify` checks the chosen query
against the business rules that change numbers silently, with one repair round.

Human in the loop: the turn pauses (LangGraph interrupt) when the plan has a genuine ambiguity,
when the user asked to review every plan, or when the candidates disagree (each distinct result is
a different reading of the question, so the user picks). Clear questions run straight through.

The state is checkpointed per chat, so a turn can pause for the user and resume later. What must
never be checkpointed travels in the per-run context instead: who the user is (re-resolved from
the database on every request, resume included), the model router, the executor and the trace.
Nodes report progress through the stream writer as the same Events the chat API already streams.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer, interrupt

from app.db.executor import QueryExecutor, QueryFailed
from app.knowledge.base import KnowledgeBase
from app.knowledge.fewshots import SelectedExample, select_examples
from app.knowledge.store import Hit
from app.llm.router import LLMRouter
from app.nl2sql.answer import build_notes, plain_language, result_table, synthesize
from app.nl2sql.consensus import CANDIDATE_SPECS, Candidate, reconcile
from app.nl2sql.entities import Resolution, resolve_mentions
from app.nl2sql.generate import SqlOutcome, build_context, generate_and_run, redact_wac_sql
from app.nl2sql.plan import make_plan, read_response, render_plan
from app.nl2sql.types import (
    AnalysisPlan,
    Event,
    HistoryTurn,
    ResultTable,
    SqlDraft,
    TurnResult,
    Understanding,
)
from app.nl2sql.understand import render_background, understand
from app.nl2sql.verify import Issue, check
from app.observability.trace import TurnTrace
from app.rbac.context import UserContext
from app.sqlguard.guard import GuardedQuery

log = logging.getLogger(__name__)

DOC_CHUNKS = 3
EXAMPLES = 4

MAX_REVIEWS = 2  # rounds of human review per turn; then the latest plan runs

FAILED = (
    "I couldn't build a working query for that question. Try rephrasing it, or be more "
    "specific about the product, time period or accounts you mean."
)

# Types the checkpointer may rebuild from a stored checkpoint (anything else is refused).
CHECKPOINT_TYPES = [
    ("app.nl2sql.types", name)
    for name in (
        "HistoryTurn",
        "Understanding",
        "Mention",
        "AnalysisPlan",
        "PlanQuestion",
        "SqlDraft",
        "ResultTable",
        "TurnResult",
    )
] + [
    ("app.knowledge.store", "Hit"),
    ("app.knowledge.fewshots", "SelectedExample"),
    ("app.knowledge.fewshots", "Example"),
    ("app.nl2sql.entities", "Resolution"),
    ("app.sqlguard.guard", "GuardedQuery"),
    ("app.nl2sql.consensus", "Candidate"),
    ("app.nl2sql.verify", "Issue"),
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
    hitl: bool = False  # may pause for the user (needs a checkpointer; never in evals or the CLI)
    always_review: bool = False  # the user asked to see every plan before it runs
    candidates: int = 1  # SQL candidates per turn (self-consistency when > 1)


class TurnState(TypedDict, total=False):
    question: str
    history: list[HistoryTurn]  # the chat's recent turns, verbatim
    summary: str  # the chat's older turns, compacted
    memory: str  # the user's cross-session memory
    understanding: Understanding
    docs: list[Hit]
    examples: list[SelectedExample]
    resolutions: list[Resolution]
    plan: AnalysisPlan | None
    feedback: list[str]  # the reviewer's choices and corrections, in order
    reviews: int
    reviewed: bool  # a human approved the plan that runs
    corrected: bool  # the last review typed a correction (so the revision is shown again)
    replan: bool
    candidates: list[Candidate]
    agreement: str  # unanimous | majority | split | single | none (consensus.Agreement)
    chosen_by: str  # consensus | user
    issues: list[Issue]  # verifier findings still open on the chosen query
    repaired: bool
    draft: SqlDraft | None  # the chosen candidate's
    guarded: GuardedQuery | None
    table: ResultTable | None
    result: TurnResult | None


def new_turn(
    question: str, history: list[HistoryTurn], summary: str = "", memory: str = ""
) -> TurnState:
    """A turn's input. A chat's checkpoint thread keeps the previous turn's values, so every
    per-turn key is reset here rather than inherited."""
    return TurnState(
        question=question,
        history=history,
        summary=summary,
        memory=memory,
        docs=[],
        examples=[],
        resolutions=[],
        plan=None,
        feedback=[],
        reviews=0,
        reviewed=False,
        corrected=False,
        replan=False,
        candidates=[],
        agreement="none",
        chosen_by="consensus",
        issues=[],
        repaired=False,
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
        intent, routed = await understand(
            deps.llm,
            state["question"],
            state["history"],
            deps.user,
            summary=state["summary"],
            memory=state["memory"],
        )
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


async def plan_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps = runtime.context
    _emit("stage", "planning")
    with deps.trace.stage("plan"):
        background = render_background(state["summary"], state["memory"])
        context = _context(state, deps)
        if background:
            context = f"## Background\n{background}\n\n{context}"
        plan, routed = await make_plan(deps.llm, deps.kb, deps.user, context, state["feedback"])
    deps.trace.add_llm("plan", routed)
    deps.trace.detail.setdefault("plans", []).append(plan.model_dump())
    return {"plan": plan, "replan": False}


async def review_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps, plan = runtime.context, state["plan"]
    assert plan is not None
    wanted = deps.always_review or bool(plan.open_questions)
    # After a review, ask again only to show a plan the user corrected in their own words;
    # answered choices are settled.
    settled = state["reviews"] > 0 and not state["corrected"]
    if not (deps.hitl and wanted) or settled or state["reviews"] >= MAX_REVIEWS:
        return {"replan": False}
    # Pauses the turn; the checkpoint keeps the state. On resume this node runs again from the top
    # and interrupt() returns the user's response (so nothing above it may have side effects).
    response = interrupt(
        {
            "kind": "plan_review",
            "reason": "ambiguous" if plan.open_questions else "requested",
            "plan": plan.model_dump(),
        }
    )
    review = read_response(plan, response if isinstance(response, dict) else {})
    deps.trace.detail.setdefault("reviews", []).append(
        {"plan": plan.summary, "feedback": review.feedback, "changed": review.changed}
    )
    return {
        "reviews": state["reviews"] + 1,
        "reviewed": True,
        "corrected": review.corrected,
        "feedback": state["feedback"] + review.feedback,
        "replan": review.changed,
    }


async def sql_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps = runtime.context
    _emit("stage", "writing_sql")
    context = _sql_context(state, deps)
    specs = CANDIDATE_SPECS[: deps.candidates]
    with deps.trace.stage("sql"):
        outcomes = await asyncio.gather(
            *(
                generate_and_run(
                    deps.llm,
                    deps.kb,
                    deps.executor,
                    deps.user,
                    context,
                    max_rows=deps.max_rows,
                    task=task,
                    temperature=temperature,
                )
                for task, temperature in specs
            ),
            return_exceptions=True,
        )
    candidates: list[Candidate] = []
    for (task, temperature), outcome in zip(specs, outcomes, strict=True):
        if isinstance(outcome, BaseException):  # e.g. that model's whole chain is down
            deps.trace.detail.setdefault("candidate_errors", []).append(f"{task}: {outcome!r}")
            continue
        candidates.append(await _candidate(deps, task, temperature, outcome))
    if not candidates:  # every candidate failed outright: surface the first error
        first = next(o for o in outcomes if isinstance(o, BaseException))
        raise first
    return {"candidates": candidates}


async def reconcile_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps, candidates = runtime.context, state["candidates"]
    consensus = reconcile(candidates)
    chosen, chosen_by = consensus.chosen, "consensus"
    if consensus.agreement == "split" and deps.hitl:
        # Each distinct result is a different reading of the question: the user decides.
        # (Pure until interrupt(): on resume this node re-runs from the top.)
        response = interrupt(
            {
                "kind": "disagreement",
                "options": [_option(candidates[g[0]]) for g in consensus.groups],
            }
        )
        pick = response.get("choice") if isinstance(response, dict) else None
        if isinstance(pick, int) and 0 <= pick < len(consensus.groups):
            chosen, chosen_by = consensus.groups[pick][0], "user"
    deps.trace.detail["consensus"] = {
        "agreement": consensus.agreement,
        "groups": consensus.groups,
        "chosen": chosen,
        "chosen_by": chosen_by,
    }
    update: dict[str, Any] = {"agreement": consensus.agreement, "chosen_by": chosen_by}
    if chosen is None:  # nothing ran: explain if most concluded "unanswerable", else fail
        group = consensus.groups[0] if consensus.groups else [0]
        draft = candidates[group[0]].draft if group[0] < len(candidates) else None
        return update | {"draft": draft, "guarded": None, "table": None}
    c = candidates[chosen]
    _record_sql(deps, c)
    return update | {"draft": c.draft, "guarded": c.guarded, "table": c.table}


async def verify_node(state: TurnState, runtime: Ctx) -> dict[str, Any]:
    deps, guarded, table = runtime.context, state["guarded"], state["table"]
    assert guarded is not None and table is not None
    _emit("stage", "checking")
    issues = check(guarded.full_sql, table)
    deps.trace.detail["verify"] = [i.code for i in issues]
    if not issues:
        return {"issues": []}
    # One repair round on the primary model, with the findings as review feedback.
    feedback = "\n".join(f"- {i.for_model}" for i in issues)
    context = (
        _sql_context(state, deps)
        + f"\n\n## A reviewer checked your query\n```sql\n{guarded.full_sql}\n```\n"
        + f"Problems found:\n{feedback}\nReturn the corrected query (or the same one if the "
        + "question really asks for it)."
    )
    with deps.trace.stage("repair"):
        outcome = await generate_and_run(
            deps.llm, deps.kb, deps.executor, deps.user, context, max_rows=deps.max_rows
        )
    repaired = await _candidate(deps, "sql", 0.0, outcome, label="repair")
    if not repaired.succeeded:
        return {"issues": issues, "repaired": True}
    assert repaired.guarded is not None and repaired.table is not None
    remaining = check(repaired.guarded.full_sql, repaired.table)
    deps.trace.detail["verify_after_repair"] = [i.code for i in remaining]
    _record_sql(deps, repaired)
    return {
        "issues": remaining,
        "repaired": True,
        "draft": repaired.draft,
        "guarded": repaired.guarded,
        "table": repaired.table,
    }


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
    confidence = _confidence(state)
    if state["agreement"] == "split" and state["chosen_by"] != "user":
        notes.append(
            "Independent ways of computing this gave different results; this answer uses the "
            "primary interpretation. Treat it with care."
        )
    notes += [i.for_user for i in state["issues"] if i.for_user]
    deps.trace.detail["confidence"] = confidence
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
            plan=state["plan"].model_dump() if state["plan"] else None,
            confidence=confidence,
        )
    )


# --- Routing ---------------------------------------------------------------------------------


def after_understand(state: TurnState) -> str:
    return "retrieve" if state["understanding"].intent == "data_question" else "reply"


def after_review(state: TurnState) -> str:
    return "plan" if state["replan"] else "sql"


def after_reconcile(state: TurnState) -> str:
    draft = state.get("draft")
    if state.get("table") is not None:
        return "verify"
    return "explain" if draft is not None and not draft.answerable else "fail"


def build_graph(checkpointer: Checkpointer = None) -> CompiledStateGraph[Any, Any, Any, Any]:
    g = StateGraph(TurnState, context_schema=TurnDeps)
    g.add_node("understand", understand_node)
    g.add_node("reply", reply_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("plan", plan_node)
    g.add_node("review", review_node)
    g.add_node("sql", sql_node)
    g.add_node("reconcile", reconcile_node)
    g.add_node("verify", verify_node)
    g.add_node("explain", explain_node)
    g.add_node("fail", fail_node)
    g.add_node("answer", answer_node)
    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", after_understand, ["retrieve", "reply"])
    g.add_edge("retrieve", "plan")
    g.add_edge("plan", "review")
    g.add_conditional_edges("review", after_review, ["plan", "sql"])
    g.add_edge("sql", "reconcile")
    g.add_conditional_edges("reconcile", after_reconcile, ["verify", "explain", "fail"])
    g.add_edge("verify", "answer")
    for end in ("reply", "explain", "fail", "answer"):
        g.add_edge(end, END)
    return g.compile(checkpointer=checkpointer)


# --- Helpers ---------------------------------------------------------------------------------


def _context(state: TurnState, deps: TurnDeps) -> str:
    intent, history = state["understanding"], state["history"]
    return build_context(
        _standalone(state),
        docs=state["docs"],
        examples=state["examples"],
        resolutions=state["resolutions"],
        previous=history[-1] if intent.is_follow_up and history else None,
        volume_instead_of_dollars=intent.asks_for_dollars and not deps.user.can_view_wac,
    )


def _sql_context(state: TurnState, deps: TurnDeps) -> str:
    context, plan = _context(state, deps), state["plan"]
    if plan is not None:
        context += "\n\n" + render_plan(plan, reviewed=state["reviewed"])
    return context


async def _candidate(
    deps: TurnDeps, task: str, temperature: float, outcome: SqlOutcome, *, label: str = ""
) -> Candidate:
    """A finished generation as a candidate: its result table (true count when capped) and its
    trace entries."""
    name = label or f"{task}@{temperature:g}"
    for call in outcome.llm_calls:
        deps.trace.add_llm("sql", call)
    attempts = [
        {"sql": a.sql, "failed_at": a.failed_at, "error": a.error, "autofixes": a.autofixes}
        for a in outcome.attempts
    ]
    deps.trace.detail.setdefault("sql_candidates", []).append(
        {"candidate": name, "attempts": attempts}
    )
    deps.trace.detail.setdefault("sql_attempts", attempts)  # the primary's (evals count repairs)
    c = Candidate(task, temperature, draft=outcome.draft, attempts=len(outcome.attempts))
    if outcome.result is None or outcome.guarded is None:
        return c
    guarded, result = outcome.guarded, outcome.result
    total = None
    if (guarded.limit_applied and len(result.rows) >= deps.max_rows) or result.truncated:
        total = await _count(deps, guarded.full_sql)
    c.guarded, c.table = guarded, result_table(result, total)
    return c


def _record_sql(deps: TurnDeps, c: Candidate) -> None:
    assert c.guarded is not None and c.table is not None
    deps.trace.sql_generated = c.draft.sql if c.draft else None
    deps.trace.sql_executed = c.guarded.sql
    deps.trace.row_count = c.table.row_count


def _option(c: Candidate) -> dict[str, Any]:
    """One reading of the question, as the user sees it when candidates disagree."""
    assert c.table is not None
    assumptions = c.draft.assumptions if c.draft else []
    return {
        "label": "; ".join(plain_language(a) for a in assumptions) or "Computed as planned",
        "columns": c.table.columns,
        "preview": c.table.rows[:3],
        "row_count": c.table.row_count,
    }


def _confidence(state: TurnState) -> str:
    caveats = [i for i in state["issues"] if i.for_user]  # an empty result can simply be true
    if caveats or (state["agreement"] == "split" and state["chosen_by"] != "user"):
        return "low"
    if state["agreement"] in ("unanimous", "majority") or state["chosen_by"] == "user":
        return "medium" if state["repaired"] else "high"
    return "medium"  # a single candidate produced a result


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
