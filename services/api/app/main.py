"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.core.config import Settings, get_settings
from app.db.engine import build_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = build_engine(settings)
        try:
            yield
        finally:
            await app.state.engine.dispose()

    app = FastAPI(title="NovaPharma NL-to-SQL API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
