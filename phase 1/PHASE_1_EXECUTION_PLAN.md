# Phase 1 Execution Plan

*Derived from README.md, PROJECT_STRUCTURE.md, and PHASE_1_DETAILED_PLAN.md.*

## Purpose

Execute Phase 1 (Weeks 1–2): set up the LangGraph multi-agent foundation, implement the Orchestrator with basic routing, and deliver three Information Agents (Syllabus, Administration, Topic) plus shared context and a minimal API—aligned with the scalable layout in `PROJECT_STRUCTURE.md`.

---

## Execution Order

Tasks are ordered by dependency: setup → framework → orchestrator → agents → shared services → API → tests. Each section can be treated as a checkpoint.

---

### Step 1: Project Setup & Dependencies (Week 1, Days 1–2)

| # | Task | Notes |
|---|------|--------|
| 1.1 | Verify/update `pyproject.toml`: LangGraph, LangChain, FastAPI, Uvicorn, Pydantic, python-dotenv | Match versions in PHASE_1_DETAILED_PLAN.md; ensure LangGraph ≥ 0.0.40 |
| 1.2 | Set up virtual environment; pin Python version (e.g. `.python-version`) | Already present; verify compatibility |
| 1.3 | Create `.env.example` with placeholders: `APP_ENV`, `PORT`, `DATABASE_URL`, `LLM_PROVIDER`, `LLM_API_KEY`, `MODEL_ID`, etc. | Per README Configuration |
| 1.4 | Create directory structure per **PROJECT_STRUCTURE.md** (not the shorter one in Phase 1) under `app/`: `app/api/`, `app/orchestrator/`, `app/agents/`, `app/services/`, `app/config/`, `app/utils/`, `app/tests/`, `app/scripts/` | Ensures scale-ready layout from day one |
| 1.5 | Add `app/config/settings.py` (Pydantic Settings, env-driven) | Single source for config |
| 1.6 | Add `app/config/limits.py` and `app/config/resiliency.py` stubs | Rate limits, timeouts, retries |
| 1.7 | Set up logging in `app/observability/logging.py` (e.g. structlog/loguru) | Structured logs from the start |
| 1.8 | Add `app/utils/errors.py` (typed errors) and `app/utils/ids.py` (correlation/idempotency keys) | Used by API and orchestrator |

**Checkpoint:** Dependencies install cleanly; `app/config/settings` loads from env; logging works.

---

### Step 2: LangGraph Multi-Agent Framework (Week 1, Days 3–4)

| # | Task | Notes |
|---|------|--------|
| 2.1 | Define shared types in `app/orchestrator/types.py`: `AgentRequest`, `AgentResponse`, `UserRequest`, intent enums | Pydantic models; versioned later in `app/api/schemas/v1/` |
| 2.2 | Implement `app/agents/base/base_agent.py`: `BaseAgent` protocol/class with `agent_id`, `capabilities`, `process_request()`, `get_capabilities()`, `health_check()` | Per PHASE_1_DETAILED_PLAN key classes |
| 2.3 | Implement agent registry: register agents by capability/intent; lookup by intent | In `app/orchestrator/` or `app/agents/base/` |
| 2.4 | Implement shared state/context interface: define `ContextStore` protocol in `app/services/context/store.py` | Per Phase 1.5 lightweight interfaces |
| 2.5 | Add minimal in-memory (or Redis) `ContextStore` in `app/services/context/` (e.g. `memory_store.py` or `redis_store.py`) | Agents stay stateless; state in store |
| 2.6 | Add `app/orchestrator/tracing.py` and a minimal `Tracer` protocol (e.g. no-op or console); wire correlation ID from request | Prep for observability |
| 2.7 | Agent lifecycle: initialization and health checks; optional graceful shutdown hook | Used by API health/readiness |

**Checkpoint:** BaseAgent and registry work; ContextStore stores/retrieves session; correlation ID flows through.

---

### Step 3: LLM & Resiliency Abstractions (Week 1, Day 4–5)

| # | Task | Notes |
|---|------|--------|
| 3.1 | Define `LLMProvider` protocol in `app/services/llm/provider.py` (`complete()` with timeout, model, temperature) | Per Phase 1.5 lightweight interfaces |
| 3.2 | Implement one concrete provider in `app/services/llm/openai_provider.py` (or similar); wrap with timeout/retry | Centralize LLM calls |
| 3.3 | Add `app/orchestrator/policies.py`: timeouts, retries with jitter, optional circuit breaker for outbound calls | Used by orchestrator and agents |

**Checkpoint:** One LLM call through `LLMProvider` with timeout/retry; policies reusable.

---

### Step 4: Orchestrator Agent (Week 1, Days 5–7)

| # | Task | Notes |
|---|------|--------|
| 4.1 | Implement request classification (intent) in `app/orchestrator/orchestrator_agent.py`: map user message to intent (syllabus / admin / topic / unknown) | Can use simple rules or small LLM call via `LLMProvider` |
| 4.2 | Implement `app/orchestrator/routing.py`: agent selection rules (intent → agent) | `select_agent(intent)` |
| 4.3 | Implement `OrchestratorAgent`: `route_request()`, delegate to selected agent, return single `AgentResponse` | Uses registry, ContextStore, Tracer, policies |
| 4.4 | Add request validation/sanitization and fallback for unknown/ambiguous intents | Error handling and safe defaults |
| 4.5 | Add response aggregation path (if multiple agents ever used); for Phase 1, single-agent response is enough | Stub or minimal implementation |
| 4.6 | Wire correlation/request IDs through orchestrator and into logs/traces | Per Phase 1.5 minimal adjustments |

**Checkpoint:** User request → intent → one agent → one response; correlation ID in logs.

---

### Step 5: Information Agents (Week 2, Days 1–4)

| # | Task | Notes |
|---|------|--------|
| 5.1 | **Syllabus Agent** (`app/agents/information/syllabus_agent.py`): curriculum data structure, `get_course_info`, `get_prerequisites`, `search_syllabus` | Can use in-memory or `app/services/db` later; start with in-memory/stub data |
| 5.2 | **Administration Agent** (`app/agents/information/administration_agent.py`): policy/procedure data, `get_policy`, `get_deadlines`, `explain_procedure` | Same: stub or minimal DB |
| 5.3 | **Topic Expert Agent** (`app/agents/information/topic_expert_agent.py`): concept explanations, `explain_concept`, `get_related_topics`, `assess_difficulty` | Can use LLM via `LLMProvider` + small KB |
| 5.4 | Register all three in agent registry; map intents (e.g. syllabus, admin, topic) in `app/orchestrator/routing.py` | End-to-end routing to real agents |
| 5.5 | Add shared helpers in `app/agents/shared_tools/` (e.g. `retrieval.py`, `formatting.py`) if needed | Avoid duplication across agents |

**Checkpoint:** Syllabus, Admin, and Topic agents respond correctly via orchestrator.

---

### Step 6: Shared Services & Context Manager (Week 2, Days 4–5)

| # | Task | Notes |
|---|------|--------|
| 6.1 | Context Manager: student/session state, conversation history, session persistence using `ContextStore` | Implement in `app/orchestrator` or a small `app/agents/context_manager` that uses `ContextStore` |
| 6.2 | Basic knowledge base: curriculum/content storage and simple search (in-memory or `app/services/db` + optional `app/services/vector` stub) | For syllabus/admin/topic content |
| 6.3 | Optional: cache layer for syllabus/policy lookups (`app/services/cache/redis_cache.py` or in-memory); document TTL | Per Phase 1.5 caching |

**Checkpoint:** Conversation context persists across turns; optional cache for lookups.

---

### Step 7: API Layer (Week 2, Days 5–6)

| # | Task | Notes |
|---|------|--------|
| 7.1 | Create `app/api/main.py`: FastAPI app factory, include routers | Per PROJECT_STRUCTURE |
| 7.2 | Add `app/api/deps.py`: DI/wiring for orchestrator, ContextStore, LLMProvider, config | No direct LLM/DB in routers |
| 7.3 | Add `app/api/routers/health.py`: liveness and readiness (and optional agent health) | Required for deployment |
| 7.4 | Add `app/api/routers/chat.py`: accept user message (and session_id); call orchestrator; return response; use schemas from `app/api/schemas/v1/chat.py` | Main student-facing endpoint |
| 7.5 | Add `app/api/schemas/v1/chat.py`: Pydantic request/response models (versioned) | Per PROJECT_STRUCTURE |
| 7.6 | Add `app/api/middleware/correlation.py`: attach request/correlation ID to each request | Propagate to orchestrator and logs |
| 7.7 | Add `app/api/middleware/ratelimit.py`: basic rate limiting and per-user quotas (use `app/config/limits.py`) | Per Phase 1.5 |
| 7.8 | Add `app/api/middleware/logging.py`: structured request/response logging | Optional but recommended |

**Checkpoint:** API serves chat and health; rate limiting and correlation IDs active.

---

### Step 8: Testing & Quality (Week 2, Days 6–7)

| # | Task | Notes |
|---|------|--------|
| 8.1 | Unit tests: `app/tests/unit/test_agents_*.py`, `test_orchestrator_*.py`, `test_services_*.py` | Per PROJECT_STRUCTURE and Phase 1 testing strategy |
| 8.2 | Integration tests: `app/tests/integration/test_api_flow.py`, `test_context_persistence.py`, `test_retrieval_flow.py` (or equivalent) | End-to-end request flow and context |
| 8.3 | Test error scenarios and fallbacks (unknown intent, timeouts, invalid input) | Per Phase 1 success criteria |

**Checkpoint:** Unit and integration tests pass; error paths covered.

---

### Step 9: Documentation & Deliverables (Week 2, Day 7)

| # | Task | Notes |
|---|------|--------|
| 9.1 | API documentation (OpenAPI via FastAPI); document chat and health endpoints | Per Phase 1 deliverables |
| 9.2 | Update README: setup steps, env vars, how to run API and (if any) workers | Getting Started |
| 9.3 | Add `app/scripts/run_api.sh` and optionally `app/scripts/seed_data.py`, `app/scripts/smoke_test.py` | Per PROJECT_STRUCTURE |
| 9.4 | Optional: Docker `compose.yml` or `infra/docker/` for local dev | Per PROJECT_STRUCTURE |

**Checkpoint:** New developer can run app and hit chat + health; docs and scripts in place.

---

## Phase 1.5 Items to Weave In (Where Noted Above)

- Correlation/request IDs in all requests and logs (Steps 2.6, 4.6, 7.6).
- Timeouts, retries, circuit breakers on outbound calls (Steps 3.2, 3.3).
- Stateless agents; state in `ContextStore` (Steps 2.4–2.5, 6.1).
- Strict Pydantic models for agent I/O (Steps 2.1, 7.5).
- Basic rate limiting (Step 7.7).
- Optional: vector store stub and cache (Steps 6.2, 6.3).

Defer to later phases: full Redis/Postgres, queues, OpenTelemetry export, multi-tenancy, containerization beyond optional dev Docker. All application code lives under `app/`.

---

## Success Criteria (Recap)

- Orchestrator routes requests to the correct information agent.
- Syllabus, Administration, and Topic agents answer basic queries in their domains.
- Conversation context is maintained via ContextStore.
- Chat and health API endpoints work with &lt; 2s response time for simple queries.
- Error handling and structured logging with correlation IDs in place.
- Unit and integration tests passing.

---

## File Map (Phase 1 vs PROJECT_STRUCTURE)

| Phase 1 Concept | Location in PROJECT_STRUCTURE (under `app/`) |
|-----------------|----------------------------------------------|
| Base agent, registry | `app/agents/base/`, `app/orchestrator/routing.py` |
| Orchestrator | `app/orchestrator/orchestrator_agent.py`, `routing.py`, `policies.py`, `types.py` |
| Syllabus / Admin / Topic agents | `app/agents/information/syllabus_agent.py`, `administration_agent.py`, `topic_expert_agent.py` |
| Context Manager | `ContextStore` in `app/services/context/`; used by orchestrator and agents |
| Config & logging | `app/config/settings.py`, `app/observability/logging.py` |
| API | `app/api/main.py`, `app/api/routers/chat.py`, `app/api/routers/health.py`, `app/api/schemas/v1/`, `app/api/middleware/` |
| LLM | `app/services/llm/provider.py`, `openai_provider.py` |

This execution plan keeps Phase 1 scope fixed while aligning with the scalable structure in `PROJECT_STRUCTURE.md` and the detailed tasks in `PHASE_1_DETAILED_PLAN.md`.
