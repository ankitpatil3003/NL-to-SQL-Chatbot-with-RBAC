"""Runs one NL-to-SQL turn through the LangGraph graph (app/nl2sql/graph.py) and traces it.

Yields Events as it goes (stage progress, answer text, final result) so the chat API can stream
them. Every turn, including failures, is traced to app.turn_traces.
"""

import logging
import uuid
from collections.abc import AsyncIterator
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Checkpointer
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
    ) -> None:
        self._llm = llm
        self._kb = kb
        self._executor = executor
        self._engine = engine
        self._max_rows = max_rows
        self._graph = build_graph(checkpointer)
        # checkpoint once, when the turn ends or pauses (not after every node)
        self._durability: Literal["exit"] | None = "exit" if checkpointer else None
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
        deps = TurnDeps(user, trace, self._llm, self._kb, self._executor, self._max_rows)
        # One checkpoint thread per chat: a paused turn resumes in the chat it was asked in.
        config: RunnableConfig = {
            "configurable": {"thread_id": session_id or f"adhoc-{uuid.uuid4()}"}
        }
        try:
            result = None
            async for mode, chunk in self._graph.astream(
                new_turn(question, history),
                config,
                context=deps,
                stream_mode=STREAM_MODES,
                durability=self._durability,
            ):
                if mode == "custom":
                    assert isinstance(chunk, Event)
                    yield chunk
                elif isinstance(chunk, dict) and "result" in chunk:
                    result = chunk["result"]
        except LLMUnavailable as exc:
            trace.status, trace.error = "error", str(exc)
            result = TurnResult(status="error", answer=UNAVAILABLE)
        except Exception as exc:  # never let a turn crash the stream; the trace keeps the detail
            log.exception("turn failed")
            trace.status, trace.error = "error", f"{type(exc).__name__}: {exc}"
            result = TurnResult(status="error", answer=UNEXPECTED)
        assert isinstance(result, TurnResult)
        result.title = trace.detail.get("understanding", {}).get("title") or None
        try:
            result.trace_id = await save_trace(self._engine, trace)
        except Exception:
            log.exception("could not save trace")
        yield Event("result", result)


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
