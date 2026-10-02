-- v2: cross-session memory and long-chat compaction. Additive, app schema only (idempotent).

-- One short markdown document per user: what they ask about and how they like answers. Written
-- by the assistant after answered turns, readable and editable by the user (GET/PUT /api/chat/memory).
-- Preferences only: access is always resolved from public.users and enforced by the database.
CREATE TABLE IF NOT EXISTS app.user_memory (
    user_id     TEXT PRIMARY KEY,
    content     TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rolling summary of a long chat's older turns (the newest turns stay verbatim).
ALTER TABLE app.chat_sessions ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE app.chat_sessions ADD COLUMN IF NOT EXISTS summarized_turns INTEGER NOT NULL DEFAULT 0;
