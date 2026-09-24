"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.auth import router as auth
from app.auth.repository import sync_demo_credentials
from app.core.config import Settings, get_settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor

log = logging.getLogger("app")


class _DropProbeAccessLogs(logging.Filter):
    """Health probes fire every few seconds (Docker, ALB); logging them buries real traffic."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(f'"GET {p} ' in record.getMessage() for p in ("/health", "/health/ready"))


logging.getLogger("uvicorn.access").addFilter(_DropProbeAccessLogs())


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = build_engine(settings)
        app.state.executor = QueryExecutor(settings)
        if settings.demo_password:
            written = await sync_demo_credentials(app.state.engine, settings.demo_password)
            if written:
                log.info("demo credentials set for %d users", written)
        try:
            yield
        finally:
            await app.state.executor.dispose()
            await app.state.engine.dispose()

    app = FastAPI(title="NovaPharma NL-to-SQL API", version="0.1.0", lifespan=lifespan)
    # Routes read settings via Depends(get_settings); make that resolve to *this* app's settings,
    # not a fresh read of the environment.
    app.dependency_overrides[get_settings] = lambda: settings
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
