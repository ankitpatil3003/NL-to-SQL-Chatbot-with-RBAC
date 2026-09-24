"""Async SQLAlchemy engine lifecycle. One engine per process, owned by the app lifespan."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        pool_pre_ping=True,
        connect_args={"timeout": settings.db_connect_timeout_s},
    )


async def ping(engine: AsyncEngine) -> bool:
    """True if the database answers a trivial query."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
