# Scalable Project Structure for Education Chatbot

Reasoning: to scale cleanly, separate concerns into API, orchestration, agents, shared services (LLM, context, vector, cache), background workers, and observability, with clear interfaces and async boundaries.

## Recommended project structure

```text
Education chatbot/
  pyproject.toml
  README.md
  .env.example
  .gitignore

  api/
    main.py                # FastAPI app factory (routers, middleware, rate limits)
    deps.py                # DI/wiring for providers, stores
    routers/
      health.py            # liveness/readiness
      chat.py              # user request endpoint(s)
      admin.py             # admin/policy endpoints
    middleware/
      correlation.py       # request IDs
      ratelimit.py         # per-user/tenant quotas
      logging.py           # structured logs
    schemas/               # Pydantic request/response models (versioned)
      v1/
        chat.py
        admin.py

  orchestrator/
    orchestrator_agent.py  # request classification, routing, aggregation, fallbacks
    routing.py             # agent selection rules
    policies.py            # timeouts, retries, circuit breakers
    tracing.py             # request/agent spans
    types.py               # AgentRequest/Response, enums

  agents/
    base/
      base_agent.py        # BaseAgent protocol, health check
    information/
      syllabus_agent.py
      administration_agent.py
      topic_expert_agent.py
    shared_tools/
      retrieval.py         # small retrieval helpers that agents call
      formatting.py

  services/
    llm/
      provider.py          # LLMProvider protocol
      openai_provider.py   # example concrete provider
      fallback.py          # provider failover/shadow rollout
    context/
      store.py             # ContextStore protocol
      redis_store.py       # Redis implementation (sessions/history)
    vector/
      client.py            # abstraction for pgvector/Qdrant
      pgvector_client.py
      qdrant_client.py
    cache/
      redis_cache.py       # simple cache utilities
    db/
      models.py            # durable entities (policies, syllabus metadata)
      repo.py              # repositories
      migrations/          # Alembic or SQL migrations
    queues/
      bus.py               # abstraction over Redis Streams/RabbitMQ
      redis_streams.py
      consumers.py         # shared consumer helpers (DLQ, retries)

  workers/
    fanout_worker.py       # processes fan-out agent tasks
    long_task_worker.py    # long-running tasks (embeddings, indexing)
    schedules/
      cron.py              # periodic jobs (cache warm, cleanup)

  observability/
    logging.py             # structlog/loguru config
    metrics.py             # Prometheus/OpenTelemetry metrics
    tracing.py             # OpenTelemetry setup/exporters
    dashboards/            # Grafana JSON, alerts

  config/
    settings.py            # Pydantic Settings (env-driven)
    features.py            # feature flags (rollout/shadow)
    limits.py              # rate-limit configs
    resiliency.py          # global timeouts/retry/circuit configs

  utils/
    ids.py                 # correlation/idempotency keys
    errors.py              # typed errors
    time.py
    serialization.py

  tests/
    unit/
      test_agents_*.py
      test_orchestrator_*.py
      test_services_*.py
    integration/
      test_api_flow.py
      test_context_persistence.py
      test_retrieval_flow.py
    performance/
      locustfile.py        # optional load tests
    fixtures/
      data/
      mocks/

  scripts/
    run_api.sh
    run_workers.sh
    seed_data.py
    smoke_test.py

  infra/
    docker/
      api.Dockerfile
      worker.Dockerfile
    k8s/
      api-deployment.yaml
      worker-deployment.yaml
      configmap.yaml
      secrets.yaml
      hpa.yaml
    compose.yml            # local dev
```

## Notes and guidance

### Architecture boundaries
- api uses only orchestrator interfaces and schemas; no direct LLM or DB calls.
- orchestrator calls agents and services via protocols; enforce timeouts/retries/circuit-breakers in `orchestrator/policies.py`.

### State and context
- All session/history flows through `services/context/*`; agents remain stateless.
- Durable data lives in `services/db/*`; ephemeral context in Redis via `ContextStore`.

### Async and queues
- Immediate requests stay async in API; fan-out/long tasks go to `services/queues/*` and `workers/*`.
- Define idempotency keys and deduplication for queued work.

### Observability
- Single place for logging/metrics/tracing; propagate correlation IDs from `api/middleware/correlation.py`.
- Track latency, error rate, token usage, queue depth, and cache hit rate.

### Versioning and governance
- Versioned Pydantic schemas in `api/schemas/v1` (add `v2` later).
- Document schema changes and deprecation windows.

### Multi-tenancy
- Carry `tenant_id` through `schemas`, `ContextStore`, and DB repos.
- Use schema-per-tenant or row-level security; isolate rate limits per tenant.

### Delivery and infra
- Containerize services; define readiness/liveness probes.
- Autoscale by CPU/memory/p95 latency; use feature flags for gradual rollouts.

---

For next steps, consider generating minimal file stubs for this layout or aligning `PHASE_1_IMPLEMENTATION.md` with actionable tasks and code pointers that map directly to these folders.
