-- Education Chatbot: Postgres schema (conversations, messages, jobs)
-- Run once against database education_chatbot before starting the app.
-- Example: psql -h localhost -p 5434 -U postgres -d education_chatbot -f docs/schema.sql

-- Conversations: one row per chat session (session_id links client session to this row)
CREATE TABLE IF NOT EXISTS conversations (
    id         SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NULL UNIQUE,
    user_id    VARCHAR(255) NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Messages: one row per turn (user or assistant), linked to a conversation
CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER      NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(32)  NOT NULL,
    content         TEXT         NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id_created_at
    ON messages (conversation_id, created_at DESC);

-- Jobs: async work items (e.g. code_execution, topic_search)
CREATE TABLE IF NOT EXISTS jobs (
    id              SERIAL PRIMARY KEY,
    type            VARCHAR(64)  NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    payload         JSONB        NULL,
    user_id         VARCHAR(255) NULL,
    conversation_id INTEGER      NULL REFERENCES conversations(id) ON DELETE SET NULL,
    result          JSONB        NULL,
    error           TEXT         NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ  NULL,
    finished_at     TIMESTAMPTZ  NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_created_at
    ON jobs (status, created_at);
