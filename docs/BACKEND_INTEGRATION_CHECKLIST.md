## Postgres & Redis Integration – Implementation Checklist

This checklist turns `BACKEND_INTEGRATION_MODULES.md` into concrete steps, assuming:

- You **do** use `app/config/db_redis.py`.
- *You **defer*** `users.py` *and any auth tables.*
- You **defer** a dedicated `services/jobs/service.py` until there are multiple job entrypoints.

---

### 1. Config: environment-driven settings

- **Extend `app/config/settings.py` with Postgres settings**
  - Add env-backed fields:
    - `POSTGRES_HOST`
    - `POSTGRES_PORT`
    - `POSTGRES_DB`
    - `POSTGRES_USER`
    - `POSTGRES_PASSWORD`
    - `DB_POOL_MIN_SIZE`
    - `DB_POOL_MAX_SIZE`
- **Extend `app/config/settings.py` with Redis settings**
  - Add env-backed fields:
    - `REDIS_HOST`
    - `REDIS_PORT`
    - `REDIS_PASSWORD`
    - `REDIS_DB_CACHE`
    - `REDIS_DB_QUEUES`
    - `REDIS_POOL_MAX_SIZE`
- **General config**
  - `ENV` (e.g. `local` | `staging` | `production`)
  - `WORKER_CONCURRENCY`
  - `QUEUE_CODE_EXECUTION`
  - `QUEUE_TOPIC_SEARCH`
- **Create `app/config/db_redis.py`**
  - Functions to build:
    - Postgres database URL (e.g. `postgresql+asyncpg://user:pass@host:port/db`)
    - Postgres pool options (min/max size) from settings
    - Redis URL(s) and pool options for cache and queues
  - Ensure this module is the **only** place that constructs DB/Redis URLs.

---

### 2. PostgreSQL: pool, migrations, repositories

- **Create `app/db/__init__.py`**
  - Expose helpers (e.g. `get_engine` / `get_pool` if needed).
- **Create `app/db/pool.py`**
  - Use `db_redis.py` to get Postgres URL and pool options.
  - Create a process-wide async engine / pool (e.g. SQLAlchemy async engine or `asyncpg` pool).
  - Provide startup/shutdown hooks for:
    - API process
    - Worker processes
- **Set up migrations directory `app/db/migrations/`**
  - Configure Alembic (or chosen tool) `env.py` to use the same Postgres URL.
  - Create initial migration with tables:
    - `conversations`
    - `messages`
    - `jobs`
  - Run migration locally and verify tables are created.
- **Create `app/db/repositories/__init__.py`**
- **Create `app/db/repositories/conversations.py`**
  - Implement:
    - `create_conversation(...)`
    - `append_message(conversation_id, ...)`
    - `get_conversation(conversation_id)`
    - `get_recent_messages(conversation_id, limit=...)`
- **Create `app/db/repositories/jobs.py`**
  - Implement:
    - `create_job(type, payload, status=PENDING, user_id=None, conversation_id=None, ...)`
    - `get_job(job_id)`
    - `update_job_status(job_id, status, result=None, error=None, finished_at=None)`

---

### 3. Redis: client, cache, queues

- **Create `app/infra/redis/__init__.py`**
  - Export top-level helpers (e.g. `get_cache_client`, `get_queue_client`).
- **Create `app/infra/redis/client.py`**
  - Use `db_redis.py` to:
    - Build Redis URL(s) for cache and queues.
    - Configure connection pool(s) using `REDIS_POOL_MAX_SIZE`.
  - Provide functions to obtain:
    - Cache Redis client
    - Queue Redis client (or same client with separate DB)
- **Create `app/infra/redis/cache.py`**
  - Implement helpers with consistent key naming using `ENV`:
    - `get_cached_conversation(conversation_id)`
    - `set_cached_conversation(conversation_id, payload, ttl_sec)`
    - `get_job_status(job_id)`
    - `set_job_status(job_id, payload, ttl_sec)`
    - `invalidate_conversation(conversation_id)`
  - Decide and document TTLs for:
    - Conversation cache
    - Job status cache
- **Create `app/infra/redis/queues.py`**
  - Implement:
    - `enqueue(queue_name, payload_dict)`
    - `dequeue(queue_name, timeout_sec)` (blocking or polling)
  - Use queue names from settings:
    - `QUEUE_CODE_EXECUTION`
    - `QUEUE_TOPIC_SEARCH`
  - Choose data structure (e.g. lists or streams) and keep that detail hidden behind this module.

---

### 4. ContextStore: Postgres + Redis-backed implementation

- **Create `app/services/context/postgres_store.py`**
  - Implement the existing `ContextStore` protocol from `store.py`.
  - Inject:
    - Conversation repository
    - (Optional) job or user repo if needed for summaries
    - Redis cache helpers
  - Implement methods:
    - `get` / `get_history`:
      - Try Redis cache first (`get_cached_conversation`).
      - On miss, load from Postgres and fill Redis with TTL.
    - `set`, `set_many`, `append_message`:
      - Persist to Postgres via repositories.
      - Update or invalidate Redis cache for the conversation.
    - `delete`:
      - Delete persisted data from Postgres.
      - Invalidate Redis keys.
    - Assessment / performance-related methods:
      - Persist and retrieve from Postgres.
      - Optionally cache summaries in Redis with TTL.
- **Wire into DI in `app/api/deps.py`**
  - Add a config flag (e.g. `settings.context_store_mode == "persistent"`).
  - When persistent mode is on:
    - Construct and return `PostgresContextStore` with injected repos and Redis cache.
  - When off:
    - Continue returning `MemoryStore()` as today.

---

### 5. Jobs: creation + queueing (API)

- **Update API endpoints that trigger long-running work**
  - Identify endpoints where:
    - Code execution is triggered.
    - Visualization generation (or other heavy work) is triggered.
  - For each such endpoint:
    - Use `jobs` repository to insert a new job row:
      - `status = PENDING`
      - `type` = job type identifier
      - `payload` = JSON-serializable data
      - `user_id` / `conversation_id` if available
    - Use `app/infra/redis/queues.py.enqueue` to send a message to the appropriate queue with at least:
      - `job_id`
      - Any minimal additional payload if needed.
    - Return `job_id` to the client for polling.
- **Defer** creating `app/services/jobs/service.py` until there are multiple call sites duplicating “create + enqueue”.

---

### 6. Workers: queue consumers

- **Create `app/workers/__init__.py`**
- **Create `app/workers/runner.py`**
  - Load settings.
  - Initialize Postgres pool using `app/db/pool.py`.
  - Initialize Redis clients using `app/infra/redis/client.py`.
  - Start one or more consumer loops per queue.
- **Create `app/workers/handlers/__init__.py`**
- **Create `app/workers/handlers/code_execution.py`**
  - Loop on `dequeue(QUEUE_CODE_EXECUTION, timeout_sec=...)`.
  - For each job:
    - Load job from Postgres via jobs repo.
    - Call existing code execution helper (e.g. Docker-based executor).
    - Update job row with result, status, and timestamps.
    - Optionally update Redis job-status cache.
- **Create `app/workers/handlers/topic_search.py`**
  - Same pattern for `QUEUE_TOPIC_SEARCH` jobs:
    - Load job.
    - Run topic-based search agent/service.
    - Persist result and status to Postgres.
    - Optionally update Redis job-status cache.

---

### 7. Health checks

- **Update `app/api/routers/health.py` (or equivalent)**
  - **Readiness probe:**
    - Acquire a connection from Postgres pool and run `SELECT 1`.
    - Ping Redis (e.g. `PING`).
    - Fail readiness if either Postgres or Redis is unavailable.
  - **Liveness probe:**
    - Keep simple (process up only); do **not** fail liveness on DB/Redis issues.

---

### 8. Verification and toggles

- **Environment variables**
  - Add new Postgres and Redis vars to `.env.example`.
  - Configure `.env` / deployment manifests accordingly.
- **Mode switching**
  - Verify that with persistent mode **off**, the system still uses `MemoryStore` and works as before.
  - Verify that with persistent mode **on**, conversations and jobs are persisted to Postgres and cached in Redis.
- **Smoke tests**
  - Create a conversation and confirm:
    - Data exists in `conversations` / `messages` tables.
    - Cache entries appear in Redis.
  - Trigger a long-running job and confirm:
    - `jobs` row is created with `PENDING`, then transitions to `SUCCESS` / `FAILED`.
    - Redis queue receives and delivers the job to a worker.
    - Job status cache in Redis (if enabled) reflects the latest status.

