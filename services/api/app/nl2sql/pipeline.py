"""The NL-to-SQL turn, end to end (CLAUDE.md §4.2):

  understand -> (non-data intents answered directly)
             -> retrieve docs + role-filtered examples -> resolve entities
             -> generate SQL -> guard -> scoped execute -> self-repair
             -> answer synthesis -> trace

Yields Events as it goes (stage progress, answer text, final result) so the chat API can stream
them. Every turn, including failures, is traced to app.turn_traces.
"""

import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.executor import QueryExecutor
from app.knowledge.base import KnowledgeBase
from app.knowledge.fewshots import select_examples
from app.llm.router import LLMRouter, LLMUnavailable
from app.nl2sql.answer import build_notes, result_table, synthesize
from app.nl2sql.entities import resolve_mentions
from app.nl2sql.generate import build_context, generate_and_run, redact_wac_sql
from app.nl2sql.prompts import prompts_hash
from app.nl2sql.types import Event, HistoryTurn, TurnResult
from app.nl2sql.understand import understand
from app.observability.trace import TurnTrace, save_trace
from app.rbac.context import UserContext

log = logging.getLogger(__name__)

DOC_CHUNKS = 3
EXAMPLES = 4

UNAVAILABLE = (
    "The assistant is temporarily unavailable (the language models didn't respond). "
    "Please try again in a minute."
)
FAILED = (
    "I couldn't build a working query for that question. Try rephrasing it, or be more "
    "specific about the product, time period or accounts you mean."
)
UNEXPECTED = "Something went wrong while answering that. Please try again or rephrase."


class Pipeline:
    def __init__(
        self,
        llm: LLMRouter,
        kb: KnowledgeBase,
        executor: QueryExecutor,
        engine: AsyncEngine,
        *,
        max_rows: int,
    ) -> None:
        self._llm = llm
        self._kb = kb
        self._executor = executor
        self._engine = engine
        self._max_rows = max_rows
        self.prompt_version = f"p{prompts_hash()}-c{kb.contract.content_hash}"

    async def run(
        self,
        question: str,
        history: list[HistoryTurn],
        user: UserContext,
        *,
        session_id: str | None = None,
    ) -> AsyncIterator[Event]:
        trace = TurnTrace(user.user_id, question, self.prompt_version, session_id)
        try:
            result = None
            async for event in self._turn(question, history, user, trace):
                if event.type == "result":
                    result = event.data
                else:
                    yield event
        except LLMUnavailable as exc:
            trace.status, trace.error = "error", str(exc)
            result = TurnResult(status="error", answer=UNAVAILABLE)
        except Exception as exc:  # never let a turn crash the stream; the trace keeps the detail
            log.exception("turn failed")
            trace.status, trace.error = "error", f"{type(exc).__name__}: {exc}"
            result = TurnResult(status="error", answer=UNEXPECTED)
        assert isinstance(result, TurnResult)
        try:
            result.trace_id = await save_trace(self._engine, trace)
        except Exception:
            log.exception("could not save trace")
        yield Event("result", result)

    async def _turn(
        self, question: str, history: list[HistoryTurn], user: UserContext, trace: TurnTrace
    ) -> AsyncIterator[Event]:
        yield Event("stage", "understanding")
        with trace.stage("understand"):
            intent, routed = await understand(self._llm, question, history, user)
        trace.add_llm("router", routed)
        trace.detail["understanding"] = intent.model_dump()

        if intent.intent != "data_question":
            status = {"clarify": "clarification", "out_of_scope": "refused"}.get(
                intent.intent, "answered"
            )
            trace.status = status
            yield Event("answer_delta", intent.reply)
            yield Event("result", TurnResult(status=status, answer=intent.reply))  # type: ignore[arg-type]
            return

        standalone = intent.standalone_question or question
        yield Event("stage", "retrieving")
        with trace.stage("retrieve"):
            docs = await self._kb.retriever.search(standalone, "doc", k=DOC_CHUNKS)
            if not user.can_view_wac:
                docs = redact_wac_sql(docs)
            examples = await select_examples(self._kb.retriever, standalone, user, k=EXAMPLES)
            resolutions = await resolve_mentions(
                intent.mentions, self._kb.catalog, self._executor, user
            )
        trace.detail["retrieval"] = {
            "docs": [{"id": d.item_id, "ranks": d.ranks} for d in docs],
            "examples": [{"id": e.example.id, "ranks": e.ranks} for e in examples],
        }
        trace.detail["entities"] = [r.hint() for r in resolutions]

        yield Event("stage", "writing_sql")
        previous = history[-1] if intent.is_follow_up and history else None
        context = build_context(
            standalone,
            docs=docs,
            examples=examples,
            resolutions=resolutions,
            previous=previous,
            volume_instead_of_dollars=intent.asks_for_dollars and not user.can_view_wac,
        )
        with trace.stage("sql"):
            outcome = await generate_and_run(
                self._llm, self._kb, self._executor, user, context, max_rows=self._max_rows
            )
        for call in outcome.llm_calls:
            trace.add_llm("sql", call)
        trace.detail["sql_attempts"] = [
            {"sql": a.sql, "failed_at": a.failed_at, "error": a.error, "autofixes": a.autofixes}
            for a in outcome.attempts
        ]
        if outcome.attempts:
            trace.sql_generated = outcome.attempts[-1].sql

        draft = outcome.draft
        if draft is not None and outcome.unanswerable:
            trace.status = "answered"
            answer = draft.unanswerable_reason or "That question can't be answered from this data."
            yield Event("answer_delta", answer)
            yield Event(
                "result",
                TurnResult(status="answered", answer=answer, standalone_question=standalone),
            )
            return
        if not outcome.succeeded or outcome.result is None or outcome.guarded is None:
            trace.status, trace.error = "error", "SQL attempts exhausted"
            yield Event("answer_delta", FAILED)
            yield Event(
                "result", TurnResult(status="error", answer=FAILED, standalone_question=standalone)
            )
            return

        trace.sql_executed = outcome.guarded.sql
        table = result_table(outcome.result)
        trace.row_count = table.row_count
        assert draft is not None
        notes = build_notes(
            table, user, asked_for_dollars=intent.asks_for_dollars, resolutions=resolutions
        )

        yield Event("stage", "answering")
        with trace.stage("answer"):
            answered = await synthesize(
                self._llm, standalone, user, table, assumptions=draft.assumptions, notes=notes
            )
        trace.add_llm("answer", answered)
        trace.status = "answered"
        yield Event("answer_delta", answered.response.text)
        yield Event(
            "result",
            TurnResult(
                status="answered",
                answer=answered.response.text,
                standalone_question=standalone,
                sql=outcome.guarded.sql,
                table=table,
                assumptions=draft.assumptions,
                rules_applied=draft.rules_applied,
                notes=notes,
            ),
        )


async def ask(
    pipeline: Pipeline, question: str, history: list[HistoryTurn], user: UserContext
) -> TurnResult:
    """Run a turn to completion (scripts, evals, tests)."""
    result = None
    async for event in pipeline.run(question, history, user):
        if event.type == "result":
            result = event.data
    assert isinstance(result, TurnResult)
    return result
