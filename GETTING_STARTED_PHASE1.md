# Getting Started (Phase 1)

Setup steps, environment variables, and how to run the API for the Phase 1 Education Chatbot (chat + health endpoints). For project overview and roadmap, see [README.md](README.md).

---

## Prerequisites

- **Python**: 3.13+ (see `.python-version` if present)
- **Package manager**: `uv` (recommended) or `pip` with a venv
- **Optional**: Docker for running via `infra/compose.yml`

---

## Setup

1. **Clone the repository** (if not already).

2. **Configure environment**
   - Copy `.env.example` to `.env`
   - Set at minimum for chat with LLM:
     - `LLM_API_KEY` — e.g. OpenAI API key
     - `MODEL_ID` — e.g. `gpt-4o-mini`
   - Other vars (e.g. `DATABASE_URL`, `PORT`) have defaults; override as needed.

3. **Install dependencies**
   ```bash
   uv sync
   ```
   or, with pip:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or `.venv\Scripts\activate` on Windows
   pip install -e .
   ```

4. **Optional: seed data**  
   Phase 1 uses in-memory context; syllabus/admin/topic data is stubbed or in-code. To run the optional seed script (no-op stub for Phase 1):
   ```bash
   uv run python -m app.scripts.seed_data
   ```

5. **Start the API**
   ```bash
   ./app/scripts/run_api.sh
   ```
   or directly:
   ```bash
   uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000
   ```
   Port is controlled by `PORT` in `.env` (default 8000).

---

## Environment variables (Phase 1)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `development` | Environment name |
| `PORT` | No | `8000` | API server port |
| `DATABASE_URL` | No | (see .env.example) | DB URL (Phase 1 may not use) |
| `LLM_PROVIDER` | No | `openai` | LLM provider key |
| `LLM_API_KEY` | Yes for chat | — | API key for LLM (e.g. OpenAI) |
| `MODEL_ID` | No | `gpt-4o-mini` | Model identifier |
| `VECTOR_DB_URL` | No | — | Vector DB (optional Phase 1) |
| `VECTOR_INDEX_NAME` | No | — | Index name (optional) |
| `AUTH_SECRET` / `JWT_SECRET` | No | — | Auth (optional Phase 1) |
| `TELEMETRY_ENDPOINT` | No | — | Observability (optional) |

---

## Running the API and workers

- **API only** (Phase 1): run the API as above. No separate worker process is required for chat.
- **Workers**: Phase 1 does not define background workers; `app/scripts/run_workers.sh` is for later phases.

---

## Verify

- **Health**: `GET http://localhost:8000/api/v1/live` and `GET http://localhost:8000/api/v1/ready`
- **Agent readiness**: `GET http://localhost:8000/api/v1/ready/agents`
- **Chat**: `POST http://localhost:8000/api/v1/chat` with body `{"message": "What is the syllabus for calculus?"}` (optional: `session_id`, `user_id`)
- **OpenAPI**: `http://localhost:8000/docs` (Swagger UI), `http://localhost:8000/openapi.json` (OpenAPI schema)

**Smoke test** (optional):
```bash
uv run python -m app.scripts.smoke_test
```

---

## Scripts (Phase 1)

| Script | Purpose |
|--------|---------|
| `app/scripts/run_api.sh` | Start the FastAPI server with uvicorn |
| `app/scripts/seed_data.py` | Optional seed (stub in Phase 1) |
| `app/scripts/smoke_test.py` | Hit health and chat endpoints to verify deployment |

---

## Docker (optional)

From the project root:
```bash
docker compose -f infra/compose.yml up
```
See `infra/compose.yml` for the API service and port mapping.
