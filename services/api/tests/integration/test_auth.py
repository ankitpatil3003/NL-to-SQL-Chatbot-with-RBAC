from fastapi.testclient import TestClient

from app.auth.tokens import COOKIE_NAME, issue_token
from app.core.config import Settings

from .conftest import DEMO_PASSWORD

RAM = "amy.nguyen@novapharma.com"


def login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> int:
    return client.post("/api/auth/login", json={"email": email, "password": password}).status_code


def test_login_sets_httponly_cookie_and_me_resolves_scope_from_db(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"email": RAM.upper(), "password": DEMO_PASSWORD})
    assert resp.status_code == 200
    cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie

    me = client.get("/api/auth/me").json()
    assert me["role"] == "ram"
    assert me["scope_label"] == "New York Metro territory"
    assert me["can_view_wac"] is False


def test_wrong_password_and_unknown_email_get_identical_401(client: TestClient) -> None:
    a = client.post("/api/auth/login", json={"email": RAM, "password": "nope"})
    b = client.post("/api/auth/login", json={"email": "ghost@novapharma.com", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_me_requires_a_valid_session(client: TestClient, settings: Settings) -> None:
    assert client.get("/api/auth/me").status_code == 401

    client.cookies.set(COOKIE_NAME, issue_token("U009", "forged-secret-forged-secret-forged!!", 5))
    assert client.get("/api/auth/me").status_code == 401

    client.cookies.set(COOKIE_NAME, issue_token("U999", settings.jwt_secret, 5))  # no such user
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client: TestClient) -> None:
    assert login(client, RAM) == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_every_seeded_user_can_log_in_with_expected_scope(client: TestClient) -> None:
    accounts = client.get("/api/auth/demo-accounts").json()
    assert accounts["password"] == DEMO_PASSWORD
    assert len(accounts["accounts"]) == 23
    for acct in accounts["accounts"]:
        assert login(client, acct["email"]) == 200, acct["email"]
        me = client.get("/api/auth/me").json()
        assert me["can_view_wac"] is (me["role"] == "exec")
        assert me["scope_label"] == acct["scope_label"]
