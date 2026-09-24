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
from app.knowledge.base import init_knowledge
from app.llm.factory import build_router

log = logging.getLogger("app")


class _DropProbeAccessLogs(logging.Filter):
    """Health probes fire every few seconds (Docker, ALB); logging them buries real traffic."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(f'"GET {p} ' in record.getMessage() for p in ("/health", "/health/ready"))


logging.getLogger("uvicorn.access").addFilter(_DropProbeAccessLogs())


def configure_logging(level: str) -> None:
    """Uvicorn configures only its own loggers; without this, app.* INFO logs (credential sync,
    knowledge rebuilds, LLM fallbacks) were silently dropped."""
    app_logger = logging.getLogger("app")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        app_logger.addHandler(handler)
    app_logger.setLevel(level.upper())


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = build_engine(settings)
        app.state.executor = QueryExecutor(settings)
        app.state.llm = build_router(settings)  # None when no LLM provider key is configured
        app.state.knowledge = await init_knowledge(
            app.state.engine, settings.knowledge_docs_dir, settings.embed_cache_dir
        )
        if settings.demo_password:
            # Non-fatal, like the knowledge layer: if the database is briefly unreachable at boot
            # (e.g. RDS still starting during a deploy), serve /health instead of crash-looping.
            try:
                written = await sync_demo_credentials(app.state.engine, settings.demo_password)
                if written:
                    log.info("demo credentials set for %d users", written)
            except Exception:
                log.exception("demo credential sync failed; logins may fail until restart")
        try:
            yield
        finally:
            if app.state.llm is not None:
                await app.state.llm.aclose()
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
