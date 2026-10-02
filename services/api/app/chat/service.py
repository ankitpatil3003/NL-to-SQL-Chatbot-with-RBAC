"""A chat turn: persist the question, run the pipeline, stream its events, persist the answer.

The pipeline runs in a background task that feeds a queue; the HTTP stream only reads the queue.
If the browser disconnects mid-answer (tab closed, network drop), the turn still completes and the
answer is saved, so reopening the chat shows it.
"""

import asyncio
import dataclasses
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from app.chat import compaction
from app.chat.memory import updated_memory
from app.chat.repository import ChatRepository
from app.llm.router import LLMRouter
from app.nl2sql.pipeline import Pipeline
from app.nl2sql.types import Event, HistoryTurn, TurnResult
from app.rbac.context import UserContext

log = logging.getLogger(__name__)

TITLE_MAX = 60


class SessionNotFound(Exception):
    pass


class TurnInProgress(Exception):
    """The user already has a question being answered (one at a time per user)."""


class NothingToResume(Exception):
    """The chat has no paused turn (already answered, or a newer question replaced it)."""


class BudgetExceeded(Exception):
    def __init__(self, budget_usd: float) -> None:
        super().__init__(f"daily budget ${budget_usd:.2f} spent")
        self.budget_usd = budget_usd


# Idle SSE streams get cut by proxies: CloudFront drops a response when the origin is silent
# for its read timeout. A SQL step can be quiet for 25-35s, so a comment line goes out every
# HEARTBEAT_S seconds while waiting.
HEARTBEAT_S = 10.0


def result_payload(result: TurnResult) -> dict[str, Any]:
    """What the UI needs to redraw an assistant message later (table, SQL, notes...)."""
    return {
        "status": result.status,
        "standalone_question": result.standalone_question,
        "sql": result.sql,
        "query": result.query,
        "table": dataclasses.asdict(result.table) if result.table else None,
        "assumptions": result.assumptions,
        "rules_applied": result.rules_applied,
        "notes": result.notes,
        "trace_id": result.trace_id,
        "plan": result.plan,
        "review": result.review,
        "confidence": result.confidence,
    }


def describe_resume(response: dict[str, Any]) -> str:
    """The user's side of a plan review, as the chat shows it."""
    if isinstance(response.get("choice"), int):
        return f"Use reading {response['choice'] + 1}"
    parts = [f"{q}: {a}" for q, a in (response.get("answers") or {}).items()]
    if response.get("feedback"):
        parts.append(str(response["feedback"]))
    return "; ".join(parts) if parts else "Run this plan"


def fallback_title(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= TITLE_MAX else title[: TITLE_MAX - 1].rstrip() + "…"


class ChatService:
    def __init__(
        self,
        repo: ChatRepository,
        pipeline: Pipeline,
        *,
        daily_budget_usd: float = 0,
        heartbeat_s: float = HEARTBEAT_S,
        llm: LLMRouter | None = None,
    ) -> None:
        self._repo = repo
        self._pipeline = pipeline
        self._llm = llm  # for memory and compaction; None turns both off
        self._budget = daily_budget_usd  # 0 = unlimited
        self._heartbeat_s = heartbeat_s
        self._active: set[str] = set()  # user ids with a turn in flight (per API instance)
        self._tasks: set[asyncio.Task[None]] = set()  # strong refs: running turns aren't GC'd

    async def stream_turn(
        self, user: UserContext, session_id: str | None, message: str, *, review: bool = False
    ) -> AsyncIterator[dict[str, Any]]:
        await self._admit(user)
        if session_id is None:
            session_id = await self._repo.create_session(user.user_id)
        elif await self._repo.get_session(user.user_id, session_id) is None:
            raise SessionNotFound
        sid = session_id

        def events(history: list[HistoryTurn], summary: str, memory: str) -> AsyncIterator[Event]:
            return self._pipeline.run(
                message, history, user, session_id=sid, review=review,
                summary=summary, memory=memory,
            )  # fmt: skip

        async for item in self._stream(user, sid, message, None, events):
            yield item

    async def resume_turn(
        self, user: UserContext, session_id: str, response: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        """Answer a paused turn's plan review; the graph continues from its checkpoint."""
        await self._admit(user)
        if await self._repo.get_session(user.user_id, session_id) is None:
            raise SessionNotFound
        if await self._pipeline.pending_review(session_id) is None:
            raise NothingToResume

        def events(*_: Any) -> AsyncIterator[Event]:  # the paused turn already has its context
            return self._pipeline.resume(response, user, session_id=session_id)

        text = describe_resume(response)
        async for item in self._stream(user, session_id, text, {"resume": True}, events):
            yield item

    async def _admit(self, user: UserContext) -> None:
        if user.user_id in self._active:
            raise TurnInProgress
        # Summed from turn traces, not memory: survives restarts and multiple API tasks, and
        # deleting chats can't reset it (traces outlive their chats).
        if self._budget and await self._repo.spend_last_day(user.user_id) >= self._budget:
            raise BudgetExceeded(self._budget)

    async def _stream(
        self,
        user: UserContext,
        session_id: str,
        message: str,
        message_payload: dict[str, Any] | None,
        events: Callable[[list[HistoryTurn], str, str], AsyncIterator[Event]],
    ) -> AsyncIterator[dict[str, Any]]:
        self._active.add(user.user_id)
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        task = asyncio.create_task(
            self._run(user, session_id, message, message_payload, events, queue)
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        yield {"event": "session", "data": {"session_id": session_id}}
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=self._heartbeat_s)
            except TimeoutError:
                yield {"event": "ping", "data": None}
                continue
            if item is None:
                return
            yield item

    async def _context(
        self,
        user: UserContext,
        session_id: str,
        queue: asyncio.Queue[dict[str, Any] | None],
    ) -> tuple[list[HistoryTurn], str]:
        """The chat's turns for the model: verbatim while they fit, older ones compacted."""
        turns = await self._repo.history(user.user_id, session_id)
        summary, folded = await self._repo.summary(session_id)
        recent = turns[folded:]
        if self._llm and compaction.needs_compaction(summary, recent):
            await queue.put({"event": "stage", "data": {"name": "compacting"}})
            older, recent = recent[: -compaction.KEEP_RECENT], recent[-compaction.KEEP_RECENT :]
            try:
                summary = await compaction.fold(self._llm, summary, older)
                await self._repo.save_summary(session_id, summary, folded + len(older))
            except Exception:  # keep going with the recent turns only; retried next turn
                log.exception("compaction failed")
        return recent, summary

    async def _remember(
        self, user: UserContext, question: str, result: TurnResult, current: str
    ) -> None:
        """Update the user's cross-session memory after an answer (best effort, off the stream)."""
        assert self._llm is not None
        try:
            content = await updated_memory(self._llm, current, question, result)
            if content and content != current:
                await self._repo.save_memory(user.user_id, content)
        except Exception:
            log.exception("memory update failed")

    def _spawn(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)  # strong ref until done
        task.add_done_callback(self._tasks.discard)

    async def _run(
        self,
        user: UserContext,
        session_id: str,
        message: str,
        message_payload: dict[str, Any] | None,
        events: Callable[[list[HistoryTurn], str, str], AsyncIterator[Event]],
        queue: asyncio.Queue[dict[str, Any] | None],
    ) -> None:
        try:
            history, summary = await self._context(user, session_id, queue)
            memory = (await self._repo.memory(user.user_id))[0] if self._llm else ""
            await self._repo.add_message(session_id, "user", message, message_payload)
            result: TurnResult | None = None
            async for event in events(history, summary, memory):
                if event.type == "stage":
                    await queue.put({"event": "stage", "data": {"name": event.data}})
                elif event.type == "answer_delta":
                    await queue.put({"event": "answer_delta", "data": {"text": event.data}})
                else:
                    result = event.data
            assert result is not None
            payload = result_payload(result)
            message_id = await self._repo.add_message(
                session_id, "assistant", result.answer, payload
            )
            if result.trace_id:
                await self._repo.link_trace(result.trace_id, message_id)
            await queue.put(
                {
                    "event": "result",
                    "data": {"message_id": message_id, "answer": result.answer, **payload},
                }
            )
            title = result.title or fallback_title(message)
            if await self._repo.set_title_if_empty(session_id, title):
                await queue.put({"event": "title", "data": {"title": title}})
            await queue.put({"event": "done", "data": {}})
            if self._llm and result.status == "answered" and result.table is not None:
                self._spawn(self._remember(user, message, result, memory))
        except Exception:
            log.exception("chat turn failed")
            await queue.put(
                {"event": "error", "data": {"message": "Something went wrong. Please try again."}}
            )
        finally:
            self._active.discard(user.user_id)
            await queue.put(None)
