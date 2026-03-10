# Getting Started

Setup, environment variables, and how to run the Education Chatbot API. For project overview and roadmap, see [README.md](README.md).

---

## Prerequisites

- **Python**: 3.13+ (see `.python-version` if present)
- **Package manager**: [uv](https://docs.astral.sh/uv/) (recommended) or pip with a venv
- **Optional**: Docker for running via `infra/compose.yml`
- **Optional for full stack**: PostgreSQL, Redis (in-memory context is supported for chat and some features)

---

## Setup

1. **Clone the repository** (if not already).

2. **Configure environment**
   - Copy `.env.example` to `.env`
   - For chat with an LLM, set at least:
     - **OpenAI**: `OPENAI_API_KEY`, `MODEL_ID` (e.g. `gpt-4o-mini`). `LLM_PROVIDER=openai` is default.
     - **Google**: `GOOGLE_API_KEY`, `MODEL_ID`, and `LLM_PROVIDER=google` (or as per your provider key).
   - Other vars (e.g. `DATABASE_URL`, `PORT`, `REDIS_*`) have defaults in `.env.example`; override as needed.

3. **Install dependencies**
   ```bash
   uv sync
   ```
   Or with pip:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or `.venv\Scripts\activate` on Windows
   pip install -e .
   ```

4. **Optional: seed data**  
   Syllabus/admin/topic data is stubbed or in-code; question bank is in-code (see `app/agents/shared_tools/question_bank.py`). To run the optional seed script:
   ```bash
   uv run python -m app.scripts.seed_data
   ```

5. **Start the API**
   ```bash
   ./app/scripts/run_api.sh
   ```
   Or directly:
   ```bash
   uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000
   ```
   Port is controlled by `PORT` in `.env` (default 8000).

---

## Environment variables

See `.env.example` for the full list. Summary of the main ones:

| Variable | Required for chat | Default | Description |
|----------|-------------------|---------|-------------|
| `APP_ENV` | No | `development` | Environment name |
| `PORT` | No | `8000` | API server port |
| `DATABASE_URL` | No* | (see .env.example) | PostgreSQL URL (legacy) |
| `POSTGRES_*` | No* | — | Granular Postgres config (host, port, db, user, password, pool) |
| `REDIS_HOST`, `REDIS_PORT`, etc. | No* | — | Redis for cache/queues |
| `LLM_PROVIDER` | No | `openai` | LLM provider (`openai`, `google`, etc.) |
| `OPENAI_API_KEY` | Yes (if OpenAI) | — | OpenAI API key |
| `GOOGLE_API_KEY` | Yes (if Google) | — | Google AI API key |
| `MODEL_ID` | No | `gpt-4o-mini` | Model identifier |
| `INTENT_DETECTION_MODE` | No | `keyword` | Intent routing: `keyword` or `llm_first` |
| `VECTOR_DB_URL`, `VECTOR_INDEX_NAME` | No | — | Vector store (optional) |
| `AUTH_SECRET` / `JWT_SECRET` | No | — | Auth (optional) |
| `TELEMETRY_ENDPOINT` | No | — | Observability (optional) |

\* Required only when using DB/Redis-backed features (e.g. conversations, readiness checks, async programming-test jobs).

---

## Running the API and workers

- **API**: Run the API as above. No separate worker is required for chat, assessments, or problem-solving.
- **Workers**: For async programming-test code execution (submit-job), run `app/scripts/run_workers.sh` so the code execution queue is processed. Otherwise use the synchronous `programming-test/submit` endpoint.

---

## API endpoints

All endpoints are under the base path **`/api/v1`**. OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs), schema: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json).

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/live` | Liveness probe; process is running (no DB/Redis). |
| GET | `/ready` | Readiness probe; Postgres and Redis healthy. |
| GET | `/ready/agents` | Readiness including agent health; returns `unhealthy_agents` if any. |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send a message and get assistant response. Body: `message`, `user_id` (required), optional `session_id`. |

### Conversations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/conversations` | List recent conversations for a user. Query: `user_id` (required), `limit` (default 20, max 100). |
| GET | `/conversations/{conversation_id}/messages` | Get recent messages for a conversation. Query: `limit` (default 50, max 200). |

### Assessment

Base path: `/assessment`. Use `session_id` (required) and optional `user_id` for performance tracking.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/assessment/quiz/start` | Start a new quiz. Body: `session_id`, optional `user_id`, `topic`, `difficulty` (beginner, intermediate, advanced). |
| POST | `/assessment/quiz/answer` | Submit an answer for the current quiz question. Body: `session_id`, optional `user_id`, `answer`. |
| POST | `/assessment/concept-test/start` | Start a concept test. Body: `session_id`, optional `user_id`, `topic`. Requires LLM. |
| POST | `/assessment/concept-test/answer` | Submit an answer or finalize. Body: `session_id`, optional `user_id`, `answer` (or `"done"` to finish). |
| POST | `/assessment/programming-test/start` | Start a programming test. Body: `session_id`, optional `user_id`, `topic`, `language`. |
| POST | `/assessment/programming-test/submit` | Submit solution code for the current test (synchronous execution). Body: `session_id`, optional `user_id`, `code`. |
| POST | `/assessment/programming-test/submit-job` | Submit solution code as async job; returns `job_id` for polling. Body: `session_id`, optional `user_id`, `code`. Requires workers. |
| GET | `/assessment/performance/{user_id}` | Performance summary: `avg_score`, `weak_topics`, `strong_topics`, `alert_flag`. |

### Visualization

| Method | Path | Description |
|--------|------|-------------|
| POST | `/visualization/generate` | Generate a diagram (Mermaid) or graph (chart spec) from a description. Body: `description` (required), optional `output_type` (`diagram` or `graph`). |

### Problem-solving

| Method | Path | Description |
|--------|------|-------------|
| POST | `/problem-solving/start` | Start a problem-solving session with an image. **Multipart**: form fields `session_id`, optional `user_id`, `message`; file `image`. **JSON**: `session_id`, optional `user_id`, `image_base64`, optional `message`. |
| POST | `/problem-solving/respond` | Submit a text answer in an existing problem-solving session. Body: `session_id`, `answer` (required), optional `user_id`. |

---

## Verify

- **Health**: `GET http://localhost:8000/api/v1/live`, `GET http://localhost:8000/api/v1/ready`
- **Agent readiness**: `GET http://localhost:8000/api/v1/ready/agents`
- **Chat**: `POST http://localhost:8000/api/v1/chat` with body `{"message": "What is the syllabus for calculus?", "user_id": "u1"}` (optional: `session_id`)
- **OpenAPI**: [http://localhost:8000/docs](http://localhost:8000/docs), [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

**Smoke test** (optional):
```bash
uv run python -m app.scripts.smoke_test
```

**Example: quiz flow**
```bash
# Start quiz
curl -X POST http://localhost:8000/api/v1/assessment/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "user_id": "u1", "topic": "algebra", "difficulty": "beginner"}'

# Submit answers (repeat until response has "completed": true)
curl -X POST http://localhost:8000/api/v1/assessment/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "user_id": "u1", "answer": "5"}'

# Performance summary
curl http://localhost:8000/api/v1/assessment/performance/u1
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `app/scripts/run_api.sh` | Start the FastAPI server with uvicorn |
| `app/scripts/run_workers.sh` | Run background workers (e.g. code execution queue for programming-test submit-job) |
| `app/scripts/seed_data.py` | Optional seed; question bank is in-code |
| `app/scripts/smoke_test.py` | Hit health, chat, and assessment endpoints to verify deployment |

---

## Docker (optional)

From the project root:
```bash
docker compose -f infra/compose.yml up
```
See `infra/compose.yml` for the API service and port mapping.
