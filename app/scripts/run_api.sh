#!/usr/bin/env bash
# Start the Education Chatbot API (Phase 1). Uses PORT from env or default 8000.
set -e
cd "$(dirname "$0")/../.."
PORT="${PORT:-8000}"
exec uv run uvicorn app.api.main:app --host 0.0.0.0 --port "$PORT"
