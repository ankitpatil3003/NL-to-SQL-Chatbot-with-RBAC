"""Integration tests run against the local compose Postgres with data loaded
(uv run scripts/load_data.py --full). They skip, rather than fail, when it isn't reachable."""

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.engine import build_engine, ping
from app.main import create_app

DEMO_PASSWORD = "integration-test-pw"


def _db_reachable(settings: Settings) -> bool:
    async def check() -> bool:
        engine = build_engine(settings)
        try:
            return await ping(engine)
        finally:
            await engine.dispose()

    return asyncio.run(check())


@pytest.fixture(scope="session")
def settings() -> Settings:
    s = Settings(demo_password=DEMO_PASSWORD, db_connect_timeout_s=2)
    if not _db_reachable(s):
        pytest.skip("Postgres not reachable; run `docker compose up -d db` and load data")
    return s


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c
