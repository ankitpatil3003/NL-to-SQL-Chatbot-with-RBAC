"""Chat endpoints: the session sidebar (list / open / rename / delete) and the streaming turn."""

import csv
import io
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.auth.deps import CurrentUser
from app.chat.memory import MAX_CHARS as MEMORY_MAX_CHARS
from app.chat.repository import ChatRepository
from app.chat.service import (
    BudgetExceeded,
    ChatService,
    NothingToResume,
    SessionNotFound,
    TurnInProgress,
)
from app.core.config import Settings, get_settings
from app.db.executor import QueryExecutor, QueryFailed
from app.nl2sql.answer import jsonable
from app.rbac.context import UserContext
from app.sqlguard.guard import GuardViolation, page_query

router = APIRouter(prefix="/api/chat", tags=["chat"])

MAX_MESSAGE_CHARS = 2000


class SessionOut(BaseModel):
    session_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    message_id: str
    role: str
    content: str
    payload: dict[str, Any] | None
    created_at: datetime


class SessionDetail(SessionOut):
    messages: list[MessageOut]


class ResumeIn(BaseModel):
    """The user's response to a paused turn's plan: choices for its open questions and/or a
    correction. Neither = run the plan as proposed."""

    answers: dict[str, str] = Field(default_factory=dict, max_length=10)
    feedback: str = Field("", max_length=MAX_MESSAGE_CHARS)
    choice: int | None = Field(None, ge=0, le=10)  # which reading, when candidates disagreed

    @field_validator("answers")
    @classmethod
    def bounded(cls, v: dict[str, str]) -> dict[str, str]:
        if any(len(k) > 500 or len(a) > 500 for k, a in v.items()):
            raise ValueError("answer too long")
        return v


class RenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class TurnIn(BaseModel):
    session_id: UUID | None = None  # omit to start a new chat
    message: str = Field(max_length=MAX_MESSAGE_CHARS)
    review: bool = False  # show the analysis plan for approval before running it

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message is empty")
        return v.strip()


def _repo(request: Request) -> ChatRepository:
    return ChatRepository(request.app.state.engine)


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")


@router.get("/sessions")
async def list_sessions(request: Request, user: CurrentUser) -> list[SessionOut]:
    return [
        SessionOut(
            session_id=s.session_id, title=s.title, created_at=s.created_at, updated_at=s.updated_at
        )
        for s in await _repo(request).list_sessions(user.user_id)
    ]


@router.get("/sessions/{session_id}")
async def get_session(session_id: UUID, request: Request, user: CurrentUser) -> SessionDetail:
    repo = _repo(request)
    session = await repo.get_session(user.user_id, str(session_id))
    if session is None:
        raise _not_found()
    messages = await repo.messages(user.user_id, str(session_id))
    return SessionDetail(
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            MessageOut(
                message_id=m.message_id,
                role=m.role,
                content=m.content,
                payload=m.payload,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.patch("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def rename_session(
    session_id: UUID, body: RenameIn, request: Request, user: CurrentUser
) -> Response:
    if not await _repo(request).rename(user.user_id, str(session_id), body.title.strip()):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: UUID, request: Request, user: CurrentUser) -> Response:
    if not await _repo(request).delete(user.user_id, str(session_id)):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Memory: what the assistant remembers about the user across chats (theirs to read and edit).


class MemoryOut(BaseModel):
    content: str
    updated_at: datetime | None


class MemoryIn(BaseModel):
    content: str = Field(max_length=MEMORY_MAX_CHARS)


@router.get("/memory")
async def get_memory(request: Request, user: CurrentUser) -> MemoryOut:
    content, updated_at = await _repo(request).memory(user.user_id)
    return MemoryOut(content=content, updated_at=updated_at)


@router.put("/memory", status_code=status.HTTP_204_NO_CONTENT)
async def put_memory(body: MemoryIn, request: Request, user: CurrentUser) -> Response:
    await _repo(request).save_memory(user.user_id, body.content.strip())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/memory", status_code=status.HTTP_204_NO_CONTENT)
async def clear_memory(request: Request, user: CurrentUser) -> Response:
    await _repo(request).save_memory(user.user_id, "")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Full results: a turn returns at most query_row_limit rows inline; these re-run its stored
# query for the rest. The SQL comes from our own message payload, is re-validated by the guard
# for the user asking now, and runs on the same scoped executor, so access is exactly a new turn's.

PAGE_MAX = 500


class RowsPage(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    offset: int


async def _stored_page_sql(
    request: Request, user: UserContext, message_id: UUID, *, offset: int, limit: int
) -> str:
    payload = await _repo(request).message_payload(user.user_id, str(message_id))
    table = (payload or {}).get("table")
    sql = (payload or {}).get("query") or (payload or {}).get("sql")  # older turns: capped SQL
    if not sql or not table:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Result not found")
    try:
        return page_query(sql, user, offset=offset, limit=limit, ncols=len(table["columns"]))
    except GuardViolation:  # e.g. the user's access changed since the question was asked
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This result isn't available at your current access level"
        ) from None


def _executor(request: Request) -> QueryExecutor:
    executor: QueryExecutor = request.app.state.executor
    return executor


@router.get("/messages/{message_id}/rows")
async def result_rows(
    message_id: UUID,
    request: Request,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=PAGE_MAX),
) -> RowsPage:
    sql = await _stored_page_sql(request, user, message_id, offset=offset, limit=limit)
    try:
        result = await _executor(request).run(user, sql)
    except QueryFailed:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Couldn't load these rows") from None
    rows = [[jsonable(v) for v in row] for row in result.rows]
    return RowsPage(columns=result.columns, rows=rows, offset=offset)


@router.get("/messages/{message_id}/export")
async def export_csv(
    message_id: UUID,
    request: Request,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    sql = await _stored_page_sql(
        request, user, message_id, offset=0, limit=settings.export_row_limit
    )
    batches = _executor(request).stream(user, sql)
    try:
        header = await anext(batches)  # fail before the 200 if the query itself fails
    except QueryFailed:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Couldn't export this result") from None

    async def body() -> AsyncIterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        async for rows in batches:
            writer.writerows(rows)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()
        yield buffer.getvalue()

    return StreamingResponse(
        body(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="result.csv"'},
    )


def _sse(event: dict[str, Any]) -> str:
    if event["event"] == "ping":
        return ": ping\n\n"  # SSE comment: keeps proxies from closing an idle stream
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], default=str)}\n\n"


@router.post("/stream")
async def stream_turn(body: TurnIn, request: Request, user: CurrentUser) -> StreamingResponse:
    """Server-sent events: session -> stage* -> answer_delta -> result -> title? -> done
    (or error). Omitting session_id starts a new chat. A result with status "needs_input" means
    the turn paused for plan review: answer it with POST /sessions/{id}/resume."""
    events = _service(request).stream_turn(
        user, str(body.session_id) if body.session_id else None, body.message, review=body.review
    )
    return await _sse_response(events)


@router.post("/sessions/{session_id}/resume")
async def resume_turn(
    session_id: UUID, body: ResumeIn, request: Request, user: CurrentUser
) -> StreamingResponse:
    """Continue the chat's paused turn with the user's plan review; streams like /stream."""
    events = _service(request).resume_turn(user, str(session_id), body.model_dump())
    return await _sse_response(events)


def _service(request: Request) -> ChatService:
    service: ChatService | None = getattr(request.app.state, "chat", None)
    if service is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The assistant isn't configured")
    return service


async def _sse_response(events: AsyncIterator[dict[str, Any]]) -> StreamingResponse:
    try:
        first = await anext(events)  # surfaces ownership / concurrency errors as HTTP status codes
    except SessionNotFound:
        raise _not_found() from None
    except NothingToResume:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This plan was already answered or replaced"
        ) from None
    except BudgetExceeded:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You've reached today's usage limit. It frees up gradually over the next 24 hours.",
        ) from None
    except TurnInProgress:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "A question is already being answered"
        ) from None

    async def body_stream() -> AsyncIterator[str]:
        yield _sse(first)
        async for event in events:
            yield _sse(event)

    return StreamingResponse(
        body_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # no proxy buffering
    )
