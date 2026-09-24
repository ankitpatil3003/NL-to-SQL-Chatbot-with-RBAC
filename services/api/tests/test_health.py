from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

# Nothing listens on port 1, so every connection attempt fails fast.
UNREACHABLE_DB = Settings(
    database_url="postgresql+asyncpg://x:x@127.0.0.1:1/x", db_connect_timeout_s=1
)


def test_liveness_does_not_need_database() -> None:
    with TestClient(create_app(UNREACHABLE_DB)) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_readiness_reports_unreachable_database() -> None:
    with TestClient(create_app(UNREACHABLE_DB)) as client:
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["database"] == "unreachable"
