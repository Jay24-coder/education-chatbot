-- For existing databases: add session_id to conversations (Option B).
-- Run once if you created the DB before session_id was added to schema.sql.
-- Example: psql -h localhost -p 5434 -U postgres -d education_chatbot -f docs/migrations/001_add_session_id_to_conversations.sql

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS session_id VARCHAR(255) UNIQUE NULL;
