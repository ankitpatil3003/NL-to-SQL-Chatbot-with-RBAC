"""The LangGraph checkpointer: graph state per chat, in Postgres, in the `app` schema.

Opened with the API's own login (DATABASE_URL), never a reader login: the scoped and exec readers
have no access to app.*, so model-written SQL can't read or alter a paused turn.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.engine import make_url

from app.nl2sql.graph import CHECKPOINT_TYPES


def libpq_conninfo(database_url: str) -> str:
    """The SQLAlchemy/asyncpg URL as a libpq connection string (asyncpg's ssl=require is libpq's
    sslmode=require), with the checkpoint tables kept in the app schema."""
    url = make_url(database_url)
    return make_conninfo(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=url.password,
        sslmode=str(url.query.get("ssl", "prefer")),
        options="-c search_path=app",
    )


@asynccontextmanager
async def postgres_checkpointer(database_url: str) -> AsyncIterator[AsyncPostgresSaver]:
    pool: AsyncConnectionPool = AsyncConnectionPool(
        libpq_conninfo(database_url),
        max_size=4,
        open=False,
        # what AsyncPostgresSaver requires of its connections
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    try:
        await pool.open(wait=True, timeout=10)  # fail fast at startup, don't stall it
        saver = AsyncPostgresSaver(
            pool,  # type: ignore[arg-type]
            serde=JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_TYPES),
        )
        await saver.setup()  # creates/migrates its tables (idempotent)
        yield saver
    finally:
        await pool.close()
