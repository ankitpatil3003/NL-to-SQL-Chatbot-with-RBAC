-- Application-owned tables. Lives in its own schema so the graded base tables stay untouched.
--
-- Deliberately NO foreign keys to public.users: scripts/load_data.py TRUNCATEs the base tables on
-- every reload, and an FK would either block that or cascade-delete everyone's chat history.
-- user_id is resolved against public.users by the API on every request instead.
--
-- Knowledge-base tables (doc chunks, embeddings, few-shots) arrive with the retrieval layer, once
-- the embedding model (and so the vector dimension) is chosen.

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.credentials (
    user_id         TEXT PRIMARY KEY,
    password_hash   TEXT NOT NULL,                      -- bcrypt
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per conversation in the sidebar.
CREATE TABLE IF NOT EXISTS app.chat_sessions (
    session_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT NOT NULL,
    title           TEXT,                               -- NULL until auto-titled after the first turn
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()  -- bumped per message; drives sidebar order
);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_recent ON app.chat_sessions (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS app.chat_messages (
    message_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES app.chat_sessions ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,                      -- the question, or the natural-language answer
    payload         JSONB,                              -- assistant extras: result table, chart, SQL, assumptions
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session ON app.chat_messages (session_id, created_at);

-- One row per assistant turn: the audit + observability record (CLAUDE.md §4.2 step 11).
-- Not cascaded from chats: deleting a conversation must not erase the security audit trail.
CREATE TABLE IF NOT EXISTS app.turn_traces (
    trace_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT NOT NULL,
    session_id      UUID,
    message_id      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL,                      -- answered | refused | clarification | error
    question        TEXT NOT NULL,
    prompt_version  TEXT,
    provider        TEXT,                               -- anthropic | openrouter (after any fallback)
    model           TEXT,
    sql_generated   TEXT,                               -- as the model wrote it
    sql_executed    TEXT,                               -- after the SQL guard's rewrite
    row_count       INTEGER,
    latency_ms      INTEGER,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cost_usd        NUMERIC(10, 6),
    detail          JSONB                               -- per-stage timings, retrieval hits, retries, fallbacks, errors
);
CREATE INDEX IF NOT EXISTS ix_turn_traces_recent ON app.turn_traces (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_turn_traces_user ON app.turn_traces (user_id, created_at DESC);
