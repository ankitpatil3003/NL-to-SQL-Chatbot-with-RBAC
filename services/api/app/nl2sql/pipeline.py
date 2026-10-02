"""Runs one NL-to-SQL turn through the LangGraph graph (app/nl2sql/graph.py) and traces it.

Yields Events as it goes (stage progress, answer text, final result) so the chat API can stream
them. Every turn, including failures, is traced to app.turn_traces.
"""

import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Checkpointer, Command
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.executor import QueryExecutor
from app.knowledge.base import KnowledgeBase
from app.llm.router import LLMRouter, LLMUnavailable
from app.nl2sql.graph import TurnDeps, build_graph, new_turn
from app.nl2sql.prompts import prompts_hash
from app.nl2sql.types import Event, HistoryTurn, TurnResult
from app.observability.trace import TurnTrace, save_trace
from app.rbac.context import UserContext

log = logging.getLogger(__name__)

# custom: the Events nodes emit; values: the state after each step (the final one has the result)
STREAM_MODES: list[Literal["custom", "values"]] = ["custom", "values"]

UNAVAILABLE = (
    "The assistant is temporarily unavailable (the language models didn't respond). "
    "Please try again in a minute."
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
        checkpointer: Checkpointer = None,
        candidates: int = 1,
    ) -> None:
        self._llm = llm
        self._kb = kb
        self._executor = executor
        self._engine = engine
        self._max_rows = max_rows
        self._candidates = candidates
        self._graph = build_graph(checkpointer)
        # checkpoint once, when the turn ends or pauses (not after every node)
        self._durability: Literal["exit"] | None = "exit" if checkpointer else None
        self.prompt_version = f"p{prompts_hash()}-c{kb.contract.content_hash}"

    @property
    def can_pause(self) -> bool:
        return self._durability is not None

    async def run(
        self,
        question: str,
        history: list[HistoryTurn],
        user: UserContext,
        *,
        session_id: str | None = None,
        review: bool = False,
    ) -> AsyncIterator[Event]:
        """A new turn. `review`: the user wants to see the plan before it runs."""
        trace = TurnTrace(user.user_id, question, self.prompt_version, session_id)
        async for event in self._execute(new_turn(question, history), user, trace, review):
            yield event

    async def resume(
        self, response: dict[str, Any], user: UserContext, *, session_id: str
    ) -> AsyncIterator[Event]:
        """Continue a paused turn with the user's response to its review."""
        snapshot = await self._graph.aget_state(_thread(session_id))
        trace = TurnTrace(
            user.user_id, snapshot.values.get("question", ""), self.prompt_version, session_id
        )
        trace.detail["resumed_with"] = response
        async for event in self._execute(Command(resume=response), user, trace, False):
            yield event

    async def pending_review(self, session_id: str) -> dict[str, Any] | None:
        """What the chat's paused turn is waiting for, if it is paused."""
        if not self.can_pause:
            return None
        snapshot = await self._graph.aget_state(_thread(session_id))
        if not snapshot.interrupts:
            return None
        value = snapshot.interrupts[0].value
        return value if isinstance(value, dict) else None

    async def _execute(
        self, graph_input: Any, user: UserContext, trace: TurnTrace, review: bool
    ) -> AsyncIterator[Event]:
        deps = TurnDeps(
            user, trace, self._llm, self._kb, self._executor, self._max_rows,
            hitl=self.can_pause, always_review=review, candidates=self._candidates,
        )  # fmt: skip
        # One checkpoint thread per chat: a paused turn resumes in the chat it was asked in.
        config = _thread(trace.session_id or f"adhoc-{uuid.uuid4()}")
        result: TurnResult | None = None
        try:
            async for mode, chunk in self._graph.astream(
                graph_input,
                config,
                context=deps,
                stream_mode=STREAM_MODES,
                durability=self._durability,
            ):
                if mode == "custom":
                    assert isinstance(chunk, Event)
                    yield chunk
                elif isinstance(chunk, dict) and chunk.get("__interrupt__"):
                    result = _paused(chunk["__interrupt__"][0].value, chunk)
                    trace.status = "needs_input"
                    yield Event("answer_delta", result.answer)
                elif isinstance(chunk, dict) and chunk.get("result") is not None:
                    result = chunk["result"]
        except LLMUnavailable as exc:
            trace.status, trace.error = "error", str(exc)
            result = TurnResult(status="error", answer=UNAVAILABLE)
        except Exception as exc:  # never let a turn crash the stream; the trace keeps the detail
            log.exception("turn failed")
            trace.status, trace.error = "error", f"{type(exc).__name__}: {exc}"
            result = TurnResult(status="error", answer=UNEXPECTED)
        if result is None:  # the graph ended without an answer: a bug, not a user problem
            trace.status, trace.error = "error", "graph ended without a result"
            result = TurnResult(status="error", answer=UNEXPECTED)
        result.title = trace.detail.get("understanding", {}).get("title") or None
        try:
            result.trace_id = await save_trace(self._engine, trace)
        except Exception:
            log.exception("could not save trace")
        yield Event("result", result)


def _thread(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id}}


def _paused(review: dict[str, Any], state: dict[str, Any]) -> TurnResult:
    plan = review.get("plan") or {}
    summary = plan.get("summary", "")
    if review.get("kind") == "disagreement":
        answer = (
            "I computed this a few independent ways and they disagree, which usually means the "
            "question can be read more than one way. Which of these did you mean?"
        )
    elif review.get("reason") == "ambiguous":
        answer = f"Before I run this, I need one choice from you. My plan: {summary}"
    else:
        answer = f"Here's my plan: {summary} Run it as is, or tell me what to change."
    understanding = state.get("understanding")
    return TurnResult(
        status="needs_input",
        answer=answer,
        standalone_question=understanding.standalone_question if understanding else None,
        review=review,
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
