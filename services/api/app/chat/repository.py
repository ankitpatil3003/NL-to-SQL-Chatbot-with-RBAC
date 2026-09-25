"""Chat persistence (app.chat_sessions / app.chat_messages). Every query is filtered by the owner's
user_id: another user's session is indistinguishable from a missing one (404, never 403)."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.nl2sql.types import HistoryTurn

HISTORY_TURNS = 4


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredMessage:
    message_id: str
    role: str
    content: str
    payload: dict[str, Any] | None
    created_at: datetime


class ChatRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def list_sessions(self, user_id: str, limit: int = 100) -> list[SessionSummary]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(
                text(
                    "SELECT session_id, title, created_at, updated_at FROM app.chat_sessions "
                    "WHERE user_id = :u ORDER BY updated_at DESC LIMIT :n"
                ),
                {"u": user_id, "n": limit},
            )
            return [
                SessionSummary(str(r.session_id), r.title, r.created_at, r.updated_at) for r in rows
            ]

    async def create_session(self, user_id: str) -> str:
        async with self._engine.begin() as conn:
            session_id = await conn.scalar(
                text("INSERT INTO app.chat_sessions (user_id) VALUES (:u) RETURNING session_id"),
                {"u": user_id},
            )
        return str(session_id)

    async def get_session(self, user_id: str, session_id: str) -> SessionSummary | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT session_id, title, created_at, updated_at FROM app.chat_sessions "
                        "WHERE session_id = CAST(:s AS uuid) AND user_id = :u"
                    ),
                    {"s": session_id, "u": user_id},
                )
            ).first()
        return (
            SessionSummary(str(row.session_id), row.title, row.created_at, row.updated_at)
            if row
            else None
        )

    async def messages(self, user_id: str, session_id: str) -> list[StoredMessage]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(
                text(
                    "SELECT m.message_id, m.role, m.content, m.payload, m.created_at "
                    "FROM app.chat_messages m JOIN app.chat_sessions s USING (session_id) "
                    "WHERE s.session_id = CAST(:s AS uuid) AND s.user_id = :u "
                    # role DESC puts 'user' before 'assistant' if timestamps ever tie
                    "ORDER BY m.created_at, m.role DESC"
                ),
                {"s": session_id, "u": user_id},
            )
            return [
                StoredMessage(str(r.message_id), r.role, r.content, r.payload, r.created_at)
                for r in rows
            ]

    async def history(self, user_id: str, session_id: str) -> list[HistoryTurn]:
        """Last completed turns as (question, answer, sql) for follow-up understanding."""
        turns: list[HistoryTurn] = []
        pending: str | None = None
        for m in await self.messages(user_id, session_id):
            if m.role == "user":
                pending = m.content
            elif pending is not None:
                sql = (m.payload or {}).get("sql")
                turns.append(HistoryTurn(pending, m.content, sql))
                pending = None
        return turns[-HISTORY_TURNS:]

    async def add_message(
        self, session_id: str, role: str, content: str, payload: dict[str, Any] | None = None
    ) -> str:
        async with self._engine.begin() as conn:
            message_id = await conn.scalar(
                text(
                    "INSERT INTO app.chat_messages (session_id, role, content, payload) "
                    "VALUES (CAST(:s AS uuid), :r, :c, CAST(:p AS jsonb)) RETURNING message_id"
                ),
                {
                    "s": session_id,
                    "r": role,
                    "c": content,
                    "p": json.dumps(payload) if payload else None,
                },
            )
            await conn.execute(
                text(
                    "UPDATE app.chat_sessions SET updated_at = now() "
                    "WHERE session_id = CAST(:s AS uuid)"
                ),
                {"s": session_id},
            )
        return str(message_id)

    async def rename(self, user_id: str, session_id: str, title: str) -> bool:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    "UPDATE app.chat_sessions SET title = :t "
                    "WHERE session_id = CAST(:s AS uuid) AND user_id = :u"
                ),
                {"t": title, "s": session_id, "u": user_id},
            )
        return result.rowcount == 1

    async def set_title_if_empty(self, session_id: str, title: str) -> bool:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    "UPDATE app.chat_sessions SET title = :t "
                    "WHERE session_id = CAST(:s AS uuid) AND title IS NULL"
                ),
                {"t": title, "s": session_id},
            )
        return result.rowcount == 1

    async def delete(self, user_id: str, session_id: str) -> bool:
        """Messages cascade; turn traces are kept (audit trail)."""
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    "DELETE FROM app.chat_sessions "
                    "WHERE session_id = CAST(:s AS uuid) AND user_id = :u"
                ),
                {"s": session_id, "u": user_id},
            )
        return result.rowcount == 1

    async def turns_last_hour(self, user_id: str) -> int:
        async with self._engine.connect() as conn:
            count = await conn.scalar(
                text(
                    "SELECT count(*) FROM app.turn_traces "
                    "WHERE user_id = :u AND created_at > now() - interval '1 hour'"
                ),
                {"u": user_id},
            )
        return int(count or 0)

    async def link_trace(self, trace_id: str, message_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE app.turn_traces SET message_id = CAST(:m AS uuid) "
                    "WHERE trace_id = CAST(:t AS uuid)"
                ),
                {"m": message_id, "t": trace_id},
            )
