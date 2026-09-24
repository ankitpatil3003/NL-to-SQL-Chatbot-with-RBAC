"""Chat API over HTTP with a scripted model: streaming, persistence, follow-ups, ownership (404
for other users' chats), rename/delete, validation, and resilience to client disconnects."""

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.chat.repository import ChatRepository
from app.chat.service import ChatService, TurnInProgress
from app.core.config import Settings
from app.main import create_app
from app.nl2sql.pipeline import Pipeline
from app.nl2sql.types import SqlDraft, Understanding

from ..fakes import ScriptedProvider, scripted_router
from .conftest import DEMO_PASSWORD

RAM = "amy.nguyen@novapharma.com"
OTHER = "brian.murphy@novapharma.com"
SQL = (
    "SELECT drug_name, SUM(pack_units) AS total_units FROM sales "
    "WHERE data_source = 'distributor' AND brand_flag = 1 GROUP BY 1 ORDER BY 2 DESC"
)


def script_turn(
    fake: ScriptedProvider, question: str, *, follow_up: bool = False, title: str = "Units By Drug"
) -> None:
    """One turn = understanding (which also suggests the chat title), SQL, answer."""
    fake.add("router", Understanding(intent="data_question", standalone_question=question, is_follow_up=follow_up,
                                     asks_for_dollars=False, mentions=[], reply="", title=title))  # fmt: skip
    fake.add(
        "sql",
        SqlDraft(
            answerable=True, sql=SQL, rules_applied=["DS-1"], assumptions=[], unanswerable_reason=""
        ),
    )
    fake.add("answer", "ZENOVAX leads.")


@pytest.fixture
def api(settings: Settings) -> Iterator[tuple[TestClient, ScriptedProvider]]:
    app = create_app(settings)
    with TestClient(app) as client:
        state = app.state
        assert state.knowledge is not None, "knowledge layer must load for chat tests"
        llm, fake = scripted_router()
        pipeline = Pipeline(llm, state.knowledge, state.executor, state.engine, max_rows=1000)
        state.chat = ChatService(ChatRepository(state.engine), pipeline)
        yield client, fake


def login(client: TestClient, email: str) -> None:
    client.cookies.clear()
    assert (
        client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD}).status_code
        == 200
    )


def stream(
    client: TestClient, message: str, session_id: str | None = None
) -> list[tuple[str, dict[str, Any]]]:
    body: dict[str, Any] = {"message": message}
    if session_id:
        body["session_id"] = session_id
    events, name = [], None
    with client.stream("POST", "/api/chat/stream", json=body) as resp:
        assert resp.status_code == 200, resp.read()
        assert resp.headers["content-type"].startswith("text/event-stream")
        for line in resp.iter_lines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: ") and name:
                events.append((name, json.loads(line[6:])))
    return events


def test_new_chat_streams_persists_and_is_listed(api) -> None:  # type: ignore[no-untyped-def]
    client, fake = api
    login(client, RAM)
    script_turn(fake, "Units by drug?")
    events = stream(client, "units by drug?")
    names = [n for n, _ in events]
    assert names[0] == "session" and names[-2:] == ["title", "done"]
    assert names.count("stage") == 4 and "answer_delta" in names
    session_id = events[0][1]["session_id"]
    result = dict(events)["result"]
    assert result["status"] == "answered" and result["table"]["rows"] and "LIMIT" in result["sql"]

    sessions = client.get("/api/chat/sessions").json()
    assert sessions[0]["session_id"] == session_id and sessions[0]["title"] == "Units By Drug"
    detail = client.get(f"/api/chat/sessions/{session_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["payload"]["sql"] == result["sql"]


def test_follow_up_uses_saved_history_and_keeps_the_title(api) -> None:  # type: ignore[no-untyped-def]
    client, fake = api
    login(client, RAM)
    script_turn(fake, "Units by drug?")
    session_id = stream(client, "units by drug?")[0][1]["session_id"]
    script_turn(fake, "Units by drug by quarter", follow_up=True, title="Ignored")
    events = stream(client, "now by quarter", session_id)
    assert "title" not in [n for n, _ in events]  # only the first turn names the chat
    assert "Previous question and its SQL" in fake.last("sql").messages[0].content
    assert len(client.get(f"/api/chat/sessions/{session_id}").json()["messages"]) == 4


def test_other_users_cannot_see_or_touch_a_chat(api) -> None:  # type: ignore[no-untyped-def]
    client, fake = api
    login(client, RAM)
    script_turn(fake, "Units by drug?")
    session_id = stream(client, "units by drug?")[0][1]["session_id"]

    login(client, OTHER)
    assert session_id not in [s["session_id"] for s in client.get("/api/chat/sessions").json()]
    assert client.get(f"/api/chat/sessions/{session_id}").status_code == 404
    assert client.patch(f"/api/chat/sessions/{session_id}", json={"title": "x"}).status_code == 404
    assert client.delete(f"/api/chat/sessions/{session_id}").status_code == 404
    resp = client.post("/api/chat/stream", json={"session_id": session_id, "message": "hi"})
    assert resp.status_code == 404


def test_rename_and_delete_keep_the_trace(api) -> None:  # type: ignore[no-untyped-def]
    client, fake = api
    login(client, RAM)
    script_turn(fake, "Units by drug?")
    events = stream(client, "units by drug?")
    session_id, trace_id = events[0][1]["session_id"], dict(events)["result"]["trace_id"]

    assert (
        client.patch(f"/api/chat/sessions/{session_id}", json={"title": "Renamed"}).status_code
        == 204
    )
    assert client.get(f"/api/chat/sessions/{session_id}").json()["title"] == "Renamed"
    assert client.delete(f"/api/chat/sessions/{session_id}").status_code == 204
    assert client.get(f"/api/chat/sessions/{session_id}").status_code == 404

    engine = client.app.state.engine  # type: ignore[attr-defined]

    async def trace_exists() -> bool:
        async with engine.connect() as conn:
            row = await conn.execute(
                text("SELECT message_id FROM app.turn_traces WHERE trace_id = CAST(:t AS uuid)"),
                {"t": trace_id},
            )
            return row.scalar_one() is not None  # linked to the (now deleted) answer, still kept

    assert client.portal.call(trace_exists)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"message": "   "}, 422),
        ({"message": "x" * 2001}, 422),
        ({"message": "hi", "session_id": "not-a-uuid"}, 422),
    ],
)
def test_input_validation(api, body: dict[str, Any], code: int) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    login(client, RAM)
    assert client.post("/api/chat/stream", json=body).status_code == code


def test_chat_requires_login_and_a_configured_assistant(api) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    client.cookies.clear()
    assert client.get("/api/chat/sessions").status_code == 401
    login(client, RAM)
    client.app.state.chat = None  # type: ignore[attr-defined]
    assert client.post("/api/chat/stream", json={"message": "hi"}).status_code == 503


async def test_one_turn_at_a_time_and_disconnects_still_save_the_answer(settings: Settings) -> None:
    from app.db.engine import build_engine
    from app.db.executor import QueryExecutor
    from app.knowledge.base import init_knowledge
    from app.rbac.context import build_user_context

    engine = build_engine(settings)
    executor = QueryExecutor(settings)
    kb = await init_knowledge(engine, settings.knowledge_docs_dir, settings.embed_cache_dir)
    assert kb is not None
    llm, fake = scripted_router()
    repo = ChatRepository(engine)
    service = ChatService(repo, Pipeline(llm, kb, executor, engine, max_rows=100))
    async with engine.connect() as conn:
        row = (
            (await conn.execute(text("SELECT * FROM public.users WHERE email = :e"), {"e": RAM}))
            .mappings()
            .one()
        )
    user = build_user_context(dict(row))

    script_turn(fake, "Units by drug?")
    events = service.stream_turn(user, None, "units by drug?")
    session = await anext(events)
    with pytest.raises(TurnInProgress):  # a second question while the first is running
        await anext(service.stream_turn(user, None, "another"))
    await events.aclose()  # the browser goes away mid-answer
    for task in list(service._tasks):
        await task
    messages = await repo.messages(user.user_id, session["data"]["session_id"])
    assert [m.role for m in messages] == ["user", "assistant"]  # the answer was still saved
    await repo.delete(user.user_id, session["data"]["session_id"])
    await executor.dispose()
    await engine.dispose()
