"""A chat turn: persist the question, run the pipeline, stream its events, persist the answer.

The pipeline runs in a background task that feeds a queue; the HTTP stream only reads the queue.
If the browser disconnects mid-answer (tab closed, network drop), the turn still completes and the
answer is saved, so reopening the chat shows it.
"""

import asyncio
import dataclasses
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.chat.repository import ChatRepository
from app.nl2sql.pipeline import Pipeline
from app.nl2sql.types import TurnResult
from app.rbac.context import UserContext

log = logging.getLogger(__name__)

TITLE_MAX = 60


class SessionNotFound(Exception):
    pass


class TurnInProgress(Exception):
    """The user already has a question being answered (one at a time per user)."""


def result_payload(result: TurnResult) -> dict[str, Any]:
    """What the UI needs to redraw an assistant message later (table, SQL, notes...)."""
    return {
        "status": result.status,
        "standalone_question": result.standalone_question,
        "sql": result.sql,
        "table": dataclasses.asdict(result.table) if result.table else None,
        "assumptions": result.assumptions,
        "rules_applied": result.rules_applied,
        "notes": result.notes,
        "trace_id": result.trace_id,
    }


def fallback_title(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= TITLE_MAX else title[: TITLE_MAX - 1].rstrip() + "…"


class ChatService:
    def __init__(self, repo: ChatRepository, pipeline: Pipeline) -> None:
        self._repo = repo
        self._pipeline = pipeline
        self._active: set[str] = set()  # user ids with a turn in flight (per API instance)
        self._tasks: set[asyncio.Task[None]] = set()  # strong refs: running turns aren't GC'd

    async def stream_turn(
        self, user: UserContext, session_id: str | None, message: str
    ) -> AsyncIterator[dict[str, Any]]:
        if user.user_id in self._active:
            raise TurnInProgress
        if session_id is None:
            session_id = await self._repo.create_session(user.user_id)
        elif await self._repo.get_session(user.user_id, session_id) is None:
            raise SessionNotFound

        self._active.add(user.user_id)
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        task = asyncio.create_task(self._run(user, session_id, message, queue))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        yield {"event": "session", "data": {"session_id": session_id}}
        while (item := await queue.get()) is not None:
            yield item

    async def _run(
        self,
        user: UserContext,
        session_id: str,
        message: str,
        queue: asyncio.Queue[dict[str, Any] | None],
    ) -> None:
        try:
            history = await self._repo.history(user.user_id, session_id)
            await self._repo.add_message(session_id, "user", message)
            result: TurnResult | None = None
            async for event in self._pipeline.run(message, history, user, session_id=session_id):
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
        except Exception:
            log.exception("chat turn failed")
            await queue.put(
                {"event": "error", "data": {"message": "Something went wrong. Please try again."}}
            )
        finally:
            self._active.discard(user.user_id)
            await queue.put(None)
