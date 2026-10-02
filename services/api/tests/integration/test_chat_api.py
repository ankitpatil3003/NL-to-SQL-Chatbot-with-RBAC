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
from app.nl2sql.types import AnalysisPlan, PlanQuestion, SqlDraft, Understanding

from ..fakes import ScriptedProvider, scripted_router
from .conftest import DEMO_PASSWORD

RAM = "amy.nguyen@novapharma.com"
OTHER = "brian.murphy@novapharma.com"
SQL = (
    "SELECT drug_name, SUM(pack_units) AS total_units FROM sales "
    "WHERE data_source = 'distributor' AND brand_flag = 1 GROUP BY 1 ORDER BY 2 DESC"
)


def script_turn(
    fake: ScriptedProvider,
    question: str,
    *,
    follow_up: bool = False,
    title: str = "Units By Drug",
    sql: str = SQL,
) -> None:
    """One turn = understanding (which also suggests the chat title), SQL, answer."""
    fake.add("router", Understanding(intent="data_question", standalone_question=question, is_follow_up=follow_up,
                                     asks_for_dollars=False, mentions=[], reply="", title=title))  # fmt: skip
    fake.add(
        "sql",
        SqlDraft(
            answerable=True, sql=sql, rules_applied=["DS-1"], assumptions=[], unanswerable_reason=""
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
    assert names.count("stage") == 6 and "answer_delta" in names
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


async def _service_env(settings: Settings, **kw: Any):  # type: ignore[no-untyped-def]
    from app.db.engine import build_engine
    from app.db.executor import QueryExecutor
    from app.knowledge.base import init_knowledge
    from app.rbac.context import build_user_context

    engine = build_engine(settings)
    executor = QueryExecutor(settings)
    kb = await init_knowledge(engine, settings.knowledge_docs_dir, settings.embed_cache_dir)
    llm, fake = scripted_router()
    repo = ChatRepository(engine)
    async with engine.connect() as conn:
        row = (
            (await conn.execute(text("SELECT * FROM public.users WHERE email = :e"), {"e": RAM}))
            .mappings()
            .one()
        )
    user = build_user_context(dict(row))
    return engine, executor, kb, llm, fake, repo, user


async def test_daily_budget_sums_trace_costs(settings: Settings) -> None:
    from app.chat.service import BudgetExceeded

    engine, executor, kb, llm, fake, repo, user = await _service_env(settings)
    already = await repo.spend_last_day(user.user_id)
    async with engine.begin() as conn:  # an earlier turn that cost $0.50
        await conn.execute(
            text(
                "INSERT INTO app.turn_traces (user_id, status, question, cost_usd) "
                "VALUES (:u, 'answered', 'budget test', 0.5)"
            ),
            {"u": user.user_id},
        )
    pipeline = Pipeline(llm, kb, executor, engine, max_rows=100)
    script_turn(fake, "Units by drug?")
    service = ChatService(repo, pipeline, daily_budget_usd=already + 1.0)
    events = [e async for e in service.stream_turn(user, None, "units by drug?")]
    assert events[-1]["event"] == "done"  # $0.50 of $1.00 spent: allowed
    spent_out = ChatService(repo, pipeline, daily_budget_usd=already + 0.5)
    with pytest.raises(BudgetExceeded):
        await anext(spent_out.stream_turn(user, None, "one more"))
    await repo.delete(user.user_id, events[0]["data"]["session_id"])
    assert await repo.spend_last_day(user.user_id) >= already + 0.5  # chat deletion can't reset it
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM app.turn_traces WHERE user_id = :u AND question = 'budget test'"),
            {"u": user.user_id},
        )
    await executor.dispose()
    await engine.dispose()


async def test_idle_streams_get_heartbeats(settings: Settings) -> None:
    import asyncio

    from app.nl2sql.types import Event, TurnResult

    engine, executor, _kb, _llm, _fake, repo, user = await _service_env(settings)

    class SlowPipeline:  # stands in for a SQL step that is silent for a while
        async def run(self, question, history, user, **_):  # type: ignore[no-untyped-def]
            await asyncio.sleep(0.35)
            yield Event("result", TurnResult(status="answered", answer="ok", title="Slow"))

    service = ChatService(repo, SlowPipeline(), heartbeat_s=0.1)  # type: ignore[arg-type]
    events = [e["event"] async for e in service.stream_turn(user, None, "slow?")]
    assert events.count("ping") >= 2 and events[-1] == "done"
    sessions = await repo.list_sessions(user.user_id)
    await repo.delete(user.user_id, sessions[0].session_id)
    await executor.dispose()
    await engine.dispose()


ORGS = "SELECT org_id, org_name FROM organizations"


@pytest.fixture
def capped_api(settings: Settings) -> Iterator[tuple[TestClient, ScriptedProvider]]:
    """Inline results capped at 5 rows, so any real listing overflows."""
    app = create_app(settings)
    with TestClient(app) as client:
        state = app.state
        llm, fake = scripted_router()
        pipeline = Pipeline(llm, state.knowledge, state.executor, state.engine, max_rows=5)
        state.chat = ChatService(ChatRepository(state.engine), pipeline)
        yield client, fake


def test_capped_result_reports_true_count_and_pages_through_everything(capped_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = capped_api
    login(client, RAM)
    script_turn(fake, "List my organizations", sql=ORGS)
    result = dict(stream(client, "list my organizations"))["result"]
    table, message_id = result["table"], result["message_id"]
    assert len(table["rows"]) == 5 and table["truncated"] and table["row_count"] > 5
    assert "LIMIT" not in result["query"] and f"{table['row_count']:,} rows" in result["notes"][-1]

    seen: list[int] = []
    while len(seen) < table["row_count"]:
        page = client.get(f"/api/chat/messages/{message_id}/rows?offset={len(seen)}&limit=500")
        assert page.status_code == 200 and page.json()["columns"] == ["org_id", "org_name"]
        assert page.json()["rows"], "paging stopped before the reported total"
        seen += [r[0] for r in page.json()["rows"]]
    assert len(seen) == len(set(seen)) == table["row_count"]  # stable order: no repeats, no gaps
    end = client.get(f"/api/chat/messages/{message_id}/rows?offset={len(seen)}").json()
    assert end["rows"] == []

    csv_resp = client.get(f"/api/chat/messages/{message_id}/export")
    assert csv_resp.status_code == 200 and csv_resp.headers["content-type"].startswith("text/csv")
    lines = csv_resp.text.strip().splitlines()
    assert lines[0] == "org_id,org_name" and len(lines) == table["row_count"] + 1

    # Only the chat's owner can page or export it (row scope itself: test_rbac_executor).
    login(client, OTHER)
    assert client.get(f"/api/chat/messages/{message_id}/rows").status_code == 404
    assert client.get(f"/api/chat/messages/{message_id}/export").status_code == 404
    client.cookies.clear()
    assert client.get(f"/api/chat/messages/{message_id}/rows").status_code == 401


def test_turns_are_checkpointed_per_chat_in_the_app_schema(settings: Settings) -> None:
    """The real lifespan wiring: the API's Postgres checkpointer keeps graph state per chat."""
    app = create_app(settings)
    with TestClient(app) as client:
        state = app.state
        llm, fake = scripted_router()
        checkpointer = state.chat._pipeline._graph.checkpointer  # the one the lifespan opened
        assert checkpointer is not None
        pipeline = Pipeline(
            llm, state.knowledge, state.executor, state.engine, max_rows=1000,
            checkpointer=checkpointer,
        )  # fmt: skip
        state.chat = ChatService(ChatRepository(state.engine), pipeline)
        login(client, RAM)
        script_turn(fake, "Units by drug?")
        session_id = stream(client, "units by drug?")[0][1]["session_id"]

        async def saved() -> Any:
            return await checkpointer.aget_tuple({"configurable": {"thread_id": session_id}})

        snapshot = client.portal.call(saved)  # type: ignore[union-attr]
        assert snapshot is not None
        values = snapshot.checkpoint["channel_values"]
        assert values["result"].status == "answered" and values["table"].row_count > 0
        assert "user" not in values  # identity is per-run context, never checkpointed
        client.delete(f"/api/chat/sessions/{session_id}")


# --- Human in the loop: plan review -----------------------------------------------------------

AMBIGUOUS = AnalysisPlan(
    summary="Units for ZENOVAX accounts.", metric="Paid demand units", filters=["ZENOVAX"],
    breakdown="by account", time_window="last quarter", rules=["DS-1", "ORG-1"],
    open_questions=[PlanQuestion(question="Which account level?",
                                 options=["Health system", "Individual facility"])],
    confidence="medium",
)  # fmt: skip


@pytest.fixture
def hitl_api(settings: Settings) -> Iterator[tuple[TestClient, ScriptedProvider]]:
    """The chat API with the lifespan's Postgres checkpointer, so turns can pause and resume."""
    app = create_app(settings)
    with TestClient(app) as client:
        state = app.state
        checkpointer = state.chat._pipeline._graph.checkpointer
        assert checkpointer is not None
        llm, fake = scripted_router()
        pipeline = Pipeline(
            llm, state.knowledge, state.executor, state.engine, max_rows=1000,
            checkpointer=checkpointer,
        )  # fmt: skip
        state.chat = ChatService(ChatRepository(state.engine), pipeline)
        yield client, fake


def resume(client: TestClient, session_id: str, body: dict[str, Any]) -> list[tuple[str, Any]]:
    events, name = [], None
    with client.stream("POST", f"/api/chat/sessions/{session_id}/resume", json=body) as resp:
        assert resp.status_code == 200, resp.read()
        for line in resp.iter_lines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: ") and name:
                events.append((name, json.loads(line[6:])))
    return events


def test_ambiguous_plan_pauses_and_resumes_with_the_users_choice(hitl_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = hitl_api
    login(client, RAM)
    script_turn(fake, "ZENOVAX units by account last quarter")
    # the revised plan still lists the question: answered choices are settled, so no second pause
    fake.queues["plan"] = [AMBIGUOUS, AMBIGUOUS]
    events = stream(client, "zenovax units by account last quarter")
    session_id, paused = events[0][1]["session_id"], dict(events)["result"]
    assert paused["status"] == "needs_input" and paused["table"] is None
    assert paused["review"]["reason"] == "ambiguous"
    assert paused["review"]["plan"]["open_questions"][0]["question"] == "Which account level?"
    assert not [r for r in fake.requests if r.task == "sql"]  # nothing ran yet

    done = dict(
        resume(client, session_id, {"answers": {"Which account level?": "Individual facility"}})
    )
    assert done["result"]["status"] == "answered" and done["result"]["table"]["rows"]
    replan = fake.last("plan").messages[0].content
    assert "Which account level? -> Individual facility" in replan  # the choice reached the planner
    assert "approved by the user" in fake.last("sql").messages[0].content

    messages = client.get(f"/api/chat/sessions/{session_id}").json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[2]["content"] == "Which account level?: Individual facility"
    # nothing left to resume, and only the owner can resume
    with client.stream("POST", f"/api/chat/sessions/{session_id}/resume", json={}) as resp:
        assert resp.status_code == 409
    login(client, OTHER)
    with client.stream("POST", f"/api/chat/sessions/{session_id}/resume", json={}) as resp:
        assert resp.status_code == 404
    login(client, RAM)
    client.delete(f"/api/chat/sessions/{session_id}")


def test_always_review_shows_a_clear_plan_and_approval_runs_it_unchanged(hitl_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = hitl_api
    login(client, RAM)
    script_turn(fake, "Units by drug?")
    with client.stream(
        "POST", "/api/chat/stream", json={"message": "units by drug?", "review": True}
    ) as r:
        lines = [line for line in r.iter_lines() if line.startswith("data: ")]
    session_id = json.loads(lines[0][6:])["session_id"]
    paused = next(json.loads(x[6:]) for x in lines if '"needs_input"' in x)
    assert paused["review"]["reason"] == "requested"

    done = dict(resume(client, session_id, {}))  # approve as proposed: no re-plan
    assert done["result"]["status"] == "answered"
    assert len([r for r in fake.requests if r.task == "plan"]) == 1
    client.delete(f"/api/chat/sessions/{session_id}")


def test_a_new_question_replaces_a_paused_plan(hitl_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = hitl_api
    login(client, RAM)
    script_turn(fake, "ZENOVAX units by account")
    fake.queues["plan"] = [AMBIGUOUS]
    session_id = stream(client, "zenovax units by account")[0][1]["session_id"]
    script_turn(fake, "Units by drug?")
    assert dict(stream(client, "units by drug?", session_id))["result"]["status"] == "answered"
    with client.stream("POST", f"/api/chat/sessions/{session_id}/resume", json={}) as resp:
        assert resp.status_code == 409
    # the abandoned question stays as context (marked not run); its plan message isn't a turn
    user_id = client.get("/api/auth/me").json()["user_id"]
    repo = client.app.state.chat._repo  # type: ignore[attr-defined]
    history = client.portal.call(repo.history, user_id, session_id)  # type: ignore[union-attr]
    assert [t.question for t in history] == ["zenovax units by account", "units by drug?"]
    assert history[0].answer.startswith("(Not run")  # context for "now by quarter", not a result
    client.delete(f"/api/chat/sessions/{session_id}")


# --- Self-consistency and verification --------------------------------------------------------

TOP2 = SQL + " LIMIT 2"  # a different result: the same drugs, only the top two


def draft_of(sql: str, assumption: str = "") -> SqlDraft:
    return SqlDraft(answerable=True, sql=sql, rules_applied=["DS-1"],
                    assumptions=[assumption] if assumption else [], unanswerable_reason="")  # fmt: skip


@pytest.fixture
def consensus_api(settings: Settings) -> Iterator[tuple[TestClient, ScriptedProvider]]:
    """Three SQL candidates per turn, with the lifespan's checkpointer (so splits can pause)."""
    app = create_app(settings)
    with TestClient(app) as client:
        state = app.state
        llm, fake = scripted_router()
        pipeline = Pipeline(
            llm, state.knowledge, state.executor, state.engine, max_rows=1000,
            checkpointer=state.chat._pipeline._graph.checkpointer, candidates=3,
        )  # fmt: skip
        state.chat = ChatService(ChatRepository(state.engine), pipeline)
        yield client, fake


def script_candidates(fake: ScriptedProvider, question: str, sqls: list[SqlDraft]) -> None:
    script_turn(fake, question)
    fake.queues["sql"] = [sqls[0], sqls[1]]  # primary greedy, primary sampled
    fake.queues["sql_cross"] = [sqls[2]]


def test_agreeing_candidates_give_a_high_confidence_answer(consensus_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = consensus_api
    login(client, RAM)
    script_candidates(fake, "Units by drug?", [draft_of(SQL)] * 3)
    events = stream(client, "units by drug?")
    result = dict(events)["result"]
    assert result["status"] == "answered" and result["confidence"] == "high"
    assert len([r for r in fake.requests if r.task in ("sql", "sql_cross")]) == 3
    temps = sorted(r.temperature or 0 for r in fake.requests if r.task == "sql")
    assert temps == [0.0, 0.7]  # the same model, greedy and sampled
    client.delete(f"/api/chat/sessions/{events[0][1]['session_id']}")


def test_disagreeing_candidates_pause_and_the_users_reading_wins(consensus_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = consensus_api
    login(client, RAM)
    script_candidates(fake, "Units by drug?", [
        draft_of(SQL, "All drugs"), draft_of(TOP2, "Only the top two drugs"),
        draft_of(SQL + " LIMIT 1", "Only the leader"),
    ])  # fmt: skip
    events = stream(client, "units by drug?")
    session_id, paused = events[0][1]["session_id"], dict(events)["result"]
    assert paused["status"] == "needs_input" and paused["review"]["kind"] == "disagreement"
    labels = [o["label"] for o in paused["review"]["options"]]
    assert labels == ["All drugs", "Only the top two drugs", "Only the leader"]

    done = dict(resume(client, session_id, {"choice": 1}))["result"]
    assert done["status"] == "answered" and done["table"]["row_count"] == 2
    assert done["confidence"] == "high" and "LIMIT 2" in done["sql"]
    messages = client.get(f"/api/chat/sessions/{session_id}").json()["messages"]
    assert messages[2]["content"] == "Use reading 2"
    client.delete(f"/api/chat/sessions/{session_id}")


def test_verifier_repairs_a_query_that_mixes_data_sources(consensus_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = consensus_api
    login(client, RAM)
    mixed = "SELECT drug_name, SUM(pack_units) AS total_units FROM sales GROUP BY 1 ORDER BY 2 DESC"
    script_candidates(fake, "Units by drug?", [draft_of(mixed)] * 3)
    fake.queues["sql"].append(draft_of(SQL))  # the repair round
    events = stream(client, "units by drug?")
    result = dict(events)["result"]
    assert "data_source = 'distributor'" in result["sql"] and result["confidence"] == "medium"
    repair = fake.last("sql").messages[0].content
    assert "A reviewer checked your query" in repair and "without filtering data_source" in repair
    assert not any("combine paid demand" in n for n in result["notes"])  # fixed, so no caveat
    client.delete(f"/api/chat/sessions/{events[0][1]['session_id']}")


def test_an_unrepaired_issue_becomes_a_caveat_and_low_confidence(consensus_api) -> None:  # type: ignore[no-untyped-def]
    client, fake = consensus_api
    login(client, RAM)
    mixed = "SELECT drug_name, SUM(pack_units) AS total_units FROM sales GROUP BY 1 ORDER BY 2 DESC"
    script_candidates(fake, "Units by drug?", [draft_of(mixed)] * 3)
    fake.queues["sql"].append(draft_of(mixed))  # the model keeps it
    events = stream(client, "units by drug?")
    result = dict(events)["result"]
    assert result["confidence"] == "low"
    assert any("combine paid demand, free drug" in n for n in result["notes"])
    client.delete(f"/api/chat/sessions/{events[0][1]['session_id']}")


# --- Memory across chats, and compaction within one -------------------------------------------


async def _drain(service: ChatService) -> None:
    import asyncio

    while service._tasks:  # background work (memory updates) still running
        await asyncio.gather(*list(service._tasks), return_exceptions=True)


async def test_memory_is_learned_after_an_answer_and_used_by_the_next_chat(
    settings: Settings,
) -> None:
    engine, executor, kb, llm, fake, repo, user = await _service_env(settings)
    await repo.save_memory(user.user_id, "")
    service = ChatService(repo, Pipeline(llm, kb, executor, engine, max_rows=100), llm=llm)
    script_turn(fake, "Units by drug?")
    fake.add("memory", "## Frequently asks about\n- unit volume by drug")
    first = [e async for e in service.stream_turn(user, None, "units by drug?")]
    await _drain(service)
    assert (await repo.memory(user.user_id))[0] == "## Frequently asks about\n- unit volume by drug"
    assert "Latest question: units by drug?" in fake.last("memory").messages[0].content

    script_turn(fake, "Units by drug?")
    fake.add("memory", "## Frequently asks about\n- unit volume by drug")
    second = [e async for e in service.stream_turn(user, None, "and again?")]
    assert "- unit volume by drug" in fake.last("router").messages[0].content  # a new chat knows
    await _drain(service)
    for events in (first, second):
        await repo.delete(user.user_id, events[0]["data"]["session_id"])
    await repo.save_memory(user.user_id, "")
    async with engine.connect() as conn:  # reader logins can't reach it
        for role in ("nl2sql_scoped_reader", "nl2sql_exec_reader"):
            allowed = await conn.scalar(
                text("SELECT has_table_privilege(:r, 'app.user_memory', 'SELECT')"), {"r": role}
            )
            assert allowed is False
    await executor.dispose()
    await engine.dispose()


def test_memory_endpoints_are_per_user(api) -> None:  # type: ignore[no-untyped-def]
    client, _ = api
    login(client, RAM)
    assert (
        client.put("/api/chat/memory", json={"content": " - prefers equivalents "}).status_code
        == 204
    )
    assert client.get("/api/chat/memory").json()["content"] == "- prefers equivalents"
    login(client, OTHER)
    assert client.get("/api/chat/memory").json()["content"] == ""  # not Amy's
    login(client, RAM)
    assert client.put("/api/chat/memory", json={"content": "x" * 2001}).status_code == 422
    assert client.delete("/api/chat/memory").status_code == 204
    assert client.get("/api/chat/memory").json()["content"] == ""


async def test_long_chats_compact_older_turns_and_keep_recent_ones_verbatim(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.chat import compaction

    monkeypatch.setattr(compaction, "HISTORY_BUDGET_TOKENS", 50)  # any real chat is "long"
    engine, executor, kb, llm, fake, repo, user = await _service_env(settings)
    service = ChatService(repo, Pipeline(llm, kb, executor, engine, max_rows=100), llm=llm)
    session_id = await repo.create_session(user.user_id)
    for i in range(6):  # six earlier turns
        await repo.add_message(session_id, "user", f"question {i}")
        await repo.add_message(session_id, "assistant", f"answer {i} " + "detail " * 20)

    script_turn(fake, "Units by drug?")
    fake.add("compact", "Earlier: questions 0 and 1 about units.")
    fake.add("memory", "")
    events = [e async for e in service.stream_turn(user, session_id, "units by drug?")]
    assert {"event": "stage", "data": {"name": "compacting"}} in events
    folded = fake.last("compact").messages[0].content
    assert "question 0" in folded and "question 1" in folded and "question 2" not in folded
    assert await repo.summary(session_id) == ("Earlier: questions 0 and 1 about units.", 2)
    sent = fake.last("router").messages[0].content
    assert "Earlier: questions 0 and 1 about units." in sent
    assert "question 1" not in sent and all(f"question {i}" in sent for i in range(2, 6))
    await _drain(service)
    await repo.delete(user.user_id, session_id)
    await executor.dispose()
    await engine.dispose()


def test_results_are_artifacts_and_follow_ups_version_them(api) -> None:  # type: ignore[no-untyped-def]
    client, fake = api
    login(client, RAM)
    script_turn(fake, "Units by drug?")
    first = stream(client, "units by drug?")
    session_id, a1 = first[0][1]["session_id"], dict(first)["result"]["artifact"]
    assert a1["version"] == 1 and a1["title"]

    script_turn(fake, "Units by drug by quarter", follow_up=True)
    a2 = dict(stream(client, "now by quarter", session_id))["result"]["artifact"]
    assert a2["id"] == a1["id"] and a2["version"] == 2  # the refinement is a new version

    script_turn(fake, "Units by drug in 340B accounts")
    a3 = dict(stream(client, "something else", session_id))["result"]["artifact"]
    assert a3["id"] != a1["id"] and a3["version"] == 1
    reopened = client.get(f"/api/chat/sessions/{session_id}").json()["messages"]
    assert [m["payload"]["artifact"]["version"] for m in reopened if m["role"] == "assistant"] == [
        1,
        2,
        1,
    ]
    client.delete(f"/api/chat/sessions/{session_id}")
