"""Chat endpoints: the session sidebar (list / open / rename / delete) and the streaming turn."""

import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.auth.deps import CurrentUser
from app.chat.repository import ChatRepository
from app.chat.service import ChatService, RateLimited, SessionNotFound, TurnInProgress

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


class RenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class TurnIn(BaseModel):
    session_id: UUID | None = None  # omit to start a new chat
    message: str = Field(max_length=MAX_MESSAGE_CHARS)

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


def _sse(event: dict[str, Any]) -> str:
    if event["event"] == "ping":
        return ": ping\n\n"  # SSE comment: keeps proxies from closing an idle stream
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], default=str)}\n\n"


@router.post("/stream")
async def stream_turn(body: TurnIn, request: Request, user: CurrentUser) -> StreamingResponse:
    """Server-sent events: session -> stage* -> answer_delta -> result -> title? -> done
    (or error). Omitting session_id starts a new chat."""
    service: ChatService | None = getattr(request.app.state, "chat", None)
    if service is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The assistant isn't configured")
    events = service.stream_turn(
        user, str(body.session_id) if body.session_id else None, body.message
    )
    try:
        first = await anext(events)  # surfaces ownership / concurrency errors as HTTP status codes
    except SessionNotFound:
        raise _not_found() from None
    except RateLimited as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"You've reached the limit of {exc.limit} questions per hour. Please try again later.",
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
