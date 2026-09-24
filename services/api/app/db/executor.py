"""Runs LLM-generated SQL for a user, inside the database's own security boundary (layer L4).

Per query, on a least-privilege login chosen by role (db/20_rbac.sql):
  1. SET LOCAL statement_timeout            runaway queries die server-side
  2. rbac.set_scope(level, value)           Directors/RAMs: seal the row scope (one-shot)
  3. SET LOCAL transaction_read_only = on   after the seal; the query can't switch it back
  4. the query itself                       asyncpg sends one prepared statement, so a
                                            "SELECT ...; DROP ..." string is rejected outright
  5. ROLLBACK                               always; nothing a query does outlives it

The SQL guard (layer L3) validates the query before it gets here. This module must stay safe
even if L3 is bypassed: the scoped login can't see wac, base tables, users or app.*, and can't
re-scope, switch role, or write.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.rbac.context import UserContext

SCOPED_READER = "nl2sql_scoped_reader"
EXEC_READER = "nl2sql_exec_reader"


class QueryFailed(Exception):
    """The database rejected or aborted the query. `message` is the Postgres error, suitable for
    the self-repair loop and traces; never show it to end users verbatim."""

    def __init__(self, message: str, sqlstate: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.sqlstate = sqlstate


def _query_failed(exc: DBAPIError) -> QueryFailed:
    """Keep the parts the self-repair loop needs: the primary message *and* the hint/detail.
    (Taking the last line of str(exc) kept only the HINT and dropped the actual error.)"""
    pg = exc.orig.__cause__ if exc.orig is not None else None  # the asyncpg exception
    message = getattr(pg, "message", None) or str(exc.orig or exc).strip()
    for label in ("detail", "hint"):
        if extra := getattr(pg, label, None):
            message += f" ({label.upper()}: {extra})"
    return QueryFailed(message, getattr(pg, "sqlstate", None))


@dataclass(frozen=True, slots=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]
    truncated: bool  # more rows existed than the row limit


class QueryExecutor:
    def __init__(self, settings: Settings) -> None:
        self._timeout_ms = settings.query_timeout_ms
        self._row_limit = settings.query_row_limit
        common: dict[str, Any] = {
            "pool_size": settings.db_pool_size,
            "pool_pre_ping": True,
            "connect_args": {"timeout": settings.db_connect_timeout_s},
        }
        self._scoped = create_async_engine(
            settings.reader_url(SCOPED_READER, settings.db_scoped_reader_password), **common
        )
        self._exec = create_async_engine(
            settings.reader_url(EXEC_READER, settings.db_exec_reader_password), **common
        )

    async def run(
        self, user: UserContext, sql: str, params: dict[str, Any] | None = None
    ) -> QueryResult:
        """Run `sql` as `user`. `params` is only for the pipeline's own lookup queries (bound
        parameters); LLM-written SQL is always run without params."""
        engine = self._exec if user.scope is None else self._scoped
        async with engine.connect() as conn:
            try:
                await conn.exec_driver_sql(f"SET LOCAL statement_timeout = {int(self._timeout_ms)}")
                if user.scope is not None:
                    await conn.execute(
                        text("SELECT rbac.set_scope(:level, :value)"),
                        {"level": user.scope.level, "value": user.scope.value},
                    )
                await conn.exec_driver_sql("SET LOCAL transaction_read_only = on")
                if params is None:
                    result = await conn.exec_driver_sql(sql)
                else:
                    result = await conn.execute(text(sql), params)
                if not result.returns_rows:
                    raise QueryFailed("statement returned no rows (only SELECT is allowed)")
                rows = [tuple(r) for r in result.fetchmany(self._row_limit + 1)]
                return QueryResult(
                    columns=list(result.keys()),
                    rows=rows[: self._row_limit],
                    truncated=len(rows) > self._row_limit,
                )
            except DBAPIError as exc:
                raise _query_failed(exc) from exc
            finally:
                await conn.rollback()

    async def dispose(self) -> None:
        await self._scoped.dispose()
        await self._exec.dispose()
