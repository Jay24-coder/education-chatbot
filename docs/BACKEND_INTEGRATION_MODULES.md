# Backend Integration: Concrete Module Breakdown

This document specifies how to integrate PostgreSQL and Redis into the education-chatbot backend with a clear module layout. It aligns with the existing [ContextStore](app/services/context/store.py) protocol, [config](app/config/settings.py), [deps](app/api/deps.py), and [wiring](app/orchestrator/wiring.py).

---

## 1. Configuration (extend existing)

**File:** [app/config/settings.py](app/config/settings.py)

- **Add** environment-driven settings for Postgres and Redis (keep current `database_url` or split into host/port/db/user/password if you prefer explicit vars).
- **New variables (conceptual):**
  - Postgres: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`.
  - Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB_CACHE`, `REDIS_DB_QUEUES`, `REDIS_POOL_MAX_SIZE`.
  - General: `ENV` (e.g. `local` | `staging` | `production`), `WORKER_CONCURRENCY`, `QUEUE_CODE_EXECUTION`, `QUEUE_VISUALIZATION`.
- **Reasoning:** Single source of truth for infra; same code path for local (e.g. `localhost`) and future production (managed hostnames).

**Optional:** A small `app/config/db_redis.py` (or similar) that builds connection URLs and pool options from these settings, so the rest of the app does not duplicate URL construction.

---

## 2. PostgreSQL: connection pool and repositories

**New modules:**

| Module | Responsibility |
|--------|----------------|
| `app/db/__init__.py` | Package init; expose `get_pool`, `close_pool` if needed for lifecycle. |
| `app/db/pool.py` | Create and hold the async (or sync) Postgres connection pool (e.g. SQLAlchemy 2 async engine with pool, or `asyncpg` pool). Initialize once per process (e.g. in FastAPI lifespan or worker startup). |
| `app/db/repositories/conversations.py` | CRUD for conversations and messages: create conversation, append message, get recent messages by `conversation_id`, get conversation by id. Used by API and by a future ContextStore implementation that backs onto Postgres. |
| `app/db/repositories/jobs.py` | Job lifecycle: create job (type, payload, status=PENDING), get by id, update status/result/error/finished_at. Used by API when enqueueing and by workers when completing/failing. |
| `app/db/repositories/users.py` | (Optional, when auth is in scope.) User lookup, API key validation, usage counters. |
| `app/db/migrations/` | Alembic (or similar) for schema versions. Tables: e.g. `conversations`, `messages`, `jobs`, optionally `users`. |

**Usage:**

- **API:** On startup, create the pool in `app/db/pool.py` and inject it (or repository instances) via dependencies. Use repositories in route handlers and in any service that needs durable state.
- **Workers:** Each worker process creates its own pool at startup (same `pool.py` or shared config), then uses `repositories/jobs.py` and any other repositories as needed.

**Reasoning:** Centralizing pool creation avoids connection leaks and keeps connection count predictable. Repositories keep persistence logic in one place and reusable by both API and workers.

---

## 3. Redis: client wrapper and pools

**New modules:**

| Module | Responsibility |
|--------|----------------|
| `app/infra/redis/__init__.py` | Package init; expose `get_redis_client` or `get_cache_client` / `get_queue_client` if you split. |
| `app/infra/redis/client.py` | Build Redis connection pool(s) from settings (e.g. `redis.ConnectionPool`). One pool for “cache” and optionally one for “queues” (or one pool, two logical DBs). Provide a singleton or dependency-injected client that uses this pool. |
| `app/infra/redis/cache.py` | Cache-aside helpers: `get_cached_conversation(conversation_id)`, `set_cached_conversation(conversation_id, payload, ttl_sec)`, `get_job_status(job_id)`, `set_job_status(job_id, payload, ttl_sec)`, `invalidate_conversation(conversation_id)`. Key namespacing: e.g. `{ENV}:chat:conv:{id}:recent`, `{ENV}:job:{id}:status`. |
| `app/infra/redis/queues.py` | Enqueue/dequeue: `enqueue(queue_name, payload_dict)`, and a blocking or polling `dequeue(queue_name, timeout_sec)` (or rely on RQ/Celery for this). Use Redis lists or Streams; if using a library, this module wraps it. Queue names from config (e.g. `QUEUE_CODE_EXECUTION`, `QUEUE_VISUALIZATION`). |

**Usage:**

- **API:** Inject Redis client/cache/queue helpers via dependencies. Before/after Postgres reads, use cache helpers to avoid repeated DB round-trips for hot data (e.g. recent messages). When creating a long-running job, call `enqueue` after inserting the job row in Postgres.
- **Workers:** Use the same Redis client/queue module to consume jobs; optionally use cache to write back job status for fast polling.

**Reasoning:** One place for key naming and TTLs; consistent behavior across API and workers; easy to swap or extend (e.g. add more cache keys or queues) without touching business logic.

---

## 4. ContextStore backed by Postgres + Redis cache

**New module:** `app/services/context/postgres_store.py` (or `app/services/context/persistent_store.py`)

- **Implements** the existing [ContextStore](app/services/context/store.py) protocol.
- **Behavior:**
  - `get` / `get_history`: Try Redis cache first (e.g. `get_cached_conversation`); on miss, read from Postgres via `app/db/repositories/conversations.py`, then fill Redis with TTL.
  - `set` / `set_many` / `append_message`: Write through to Postgres; invalidate or update the Redis key for that session/conversation.
  - `delete`: Delete from Postgres; invalidate Redis.
  - Assessment/performance methods (`append_assessment_result`, `get_performance_summary`, `update_summary`): Persist and read from Postgres (and optionally cache summary in Redis with TTL).
- **Dependencies:** Conversation (and optionally user) repositories, Redis cache helper. All injected (e.g. via `deps` or constructor).

**Wiring:**

- In [app/api/deps.py](app/api/deps.py), add a switch (e.g. from `settings`) or factory: when “persistent” mode is on, return an instance of this Postgres-backed store instead of `MemoryStore()`; otherwise keep returning `MemoryStore()` for local/dev. This keeps a single `get_context_store()` used everywhere.

**Reasoning:** Existing code that depends on `ContextStore` stays unchanged; only the implementation and DI change. You get durable session and conversation state with a cache layer for hot paths.

---

## 5. Job creation and queueing (API side)

**Where:** In the API layer, wherever a long-running task is triggered (e.g. code execution, visualization generation).

- **Flow:**
  1. Insert a row in `jobs` via `app/db/repositories/jobs.py` (status=PENDING, type, payload, user_id/conversation_id, etc.).
  2. Enqueue a message to the appropriate Redis queue via `app/infra/redis/queues.py` with at least `job_id` (and optionally minimal payload).
  3. Return `job_id` to the client (e.g. in response or as polling id).

**Optional:** A small `app/services/jobs/service.py` that encapsulates “create job + enqueue” so routers stay thin.

**Reasoning:** Postgres is the source of truth for job existence and status; Redis is the transport for worker pickup. If Redis loses the message, a reconciliation job can re-enqueue from Postgres for PENDING jobs.

---

## 6. Workers: queue consumers

**New modules:**

| Module | Responsibility |
|--------|----------------|
| `app/workers/__init__.py` | Package init. |
| `app/workers/runner.py` | Entrypoint (e.g. `python -m app.workers.runner`). Load config, create Postgres pool and Redis client, start one or more consumer loops (or RQ/Celery workers). |
| `app/workers/handlers/code_execution.py` | Dequeue a code-execution job (by `job_id`), load full payload from Postgres if needed, call the existing code execution helper (e.g. `execute_in_docker`), write result back to Postgres and optionally to Redis cache. |
| `app/workers/handlers/visualization.py` | Same idea for visualization jobs: load job, run visualization agent or service, persist result, update job status. |

**Lifecycle:**

- On startup: create DB pool and Redis connection; register handlers per queue.
- Loop: block on Redis queue (or use RQ/Celery); on message, load job from Postgres, run handler, update job row; on exception, update job as FAILED and optionally retry according to policy.

**Reasoning:** Keeps long-running or heavy work off the request path; same repositories and Redis infra as the API; workers stay stateless and horizontally scalable.

---

## 7. Health checks

**Where:** [app/api/routers/health.py](app/api/routers/health.py) (or equivalent).

- **Readiness:** In addition to existing checks, optionally check:
  - Postgres: acquire a connection from the pool and run a simple query (e.g. `SELECT 1`).
  - Redis: ping (e.g. `PING`).
- **Liveness:** Keep as-is (process up). Do not fail liveness on DB/Redis; use readiness so the orchestrator can stop sending traffic to a pod that lost DB/Redis.

**Reasoning:** Ensures traffic only hits instances that can actually serve requests.

---

## 8. Dependency injection summary

| Dependency | Source | Used by |
|------------|--------|--------|
| Settings | [app/config/settings.py](app/config/settings.py) | All |
| Postgres pool | [app/db/pool.py](app/db/pool.py) | Repositories, workers |
| Conversation repo | `app/db/repositories/conversations.py` | Postgres-backed ContextStore, API |
| Jobs repo | `app/db/repositories/jobs.py` | API (job creation), workers (job update) |
| Redis cache | `app/infra/redis/cache.py` | ContextStore impl, API, optionally workers |
| Redis queues | `app/infra/redis/queues.py` | API (enqueue), workers (dequeue) |
| ContextStore | [app/api/deps.py](app/api/deps.py) | Orchestrator, routers (unchanged) |

When “persistent” mode is enabled, `get_context_store()` returns the Postgres+Redis-backed implementation; otherwise it returns `MemoryStore()`.

---

## 9. File layout (new/updated)

```
app/
  config/
    settings.py          # extend with Postgres/Redis env vars
    db_redis.py          # optional: URLs and pool options from settings
  db/
    __init__.py
    pool.py              # Postgres connection pool
    repositories/
      __init__.py
      conversations.py
      jobs.py
      users.py           # optional
    migrations/          # Alembic
      env.py
      versions/
        ...
  infra/
    redis/
      __init__.py
      client.py          # Redis connection pool(s)
      cache.py           # cache-aside helpers
      queues.py          # enqueue / dequeue
  services/
    context/
      store.py           # existing protocol
      memory_store.py    # existing in-memory impl
      postgres_store.py  # new: Postgres + Redis cache impl
  workers/
    __init__.py
    runner.py            # worker entrypoint
    handlers/
      __init__.py
      code_execution.py
      visualization.py
  api/
    deps.py              # extend: optional Postgres/Redis-backed ContextStore, job service
    routers/
      health.py          # extend: Postgres + Redis readiness
```

---

## 10. Order of implementation (suggested)

1. **Config:** Add Postgres and Redis settings; optional `db_redis.py`.
2. **Postgres:** `app/db/pool.py` + migrations for `conversations`, `messages`, `jobs`; then `repositories/conversations.py` and `repositories/jobs.py`.
3. **Redis:** `app/infra/redis/client.py`, `cache.py`, `queues.py`.
4. **ContextStore:** Implement `postgres_store.py` and wire it in `deps.py` behind a config flag.
5. **Jobs:** Use jobs repo + Redis queue in API where code execution or visualization is triggered; add optional `services/jobs/service.py`.
6. **Workers:** `runner.py` and handlers for code execution and visualization; run as separate process(es).
7. **Health:** Add Postgres and Redis checks to readiness.

This order keeps each step testable and avoids big-bang integration.
