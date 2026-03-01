# Education Chatbot — Codebase Mentoring Guide

This document explains the codebase as if you are being mentored by a senior developer. For each major area we cover: **what problem it solves**, **why it is written this way**, **how it connects to other parts**, **design patterns**, **what breaks if removed**, and **a simpler version** where useful.

---

## 1. Overall Architecture and Component Relationships

### High-level flow

```
Client (HTTP)
    → FastAPI (main.py)
        → Middleware (correlation ID, rate limit, logging)
        → Router (chat, assessment, health, visualization, problem_solving)
            → Depends (deps.py): orchestrator / agents / context store / LLM
                → OrchestratorAgent
                    → classify intent → select agent (registry) → load context (ContextStore)
                    → call agent.process_request(AgentRequest)
                    → persist turn (ContextManager) → return AgentResponse
    ← JSON response
```

- **API layer** (`app/api/`): HTTP entry point, request/response shapes, error handling, middleware.
- **Orchestrator** (`app/orchestrator/`): Single entry point for “chat”; classifies intent, routes to the right agent, applies timeout, persists conversation.
- **Agents** (`app/agents/`): Domain experts (syllabus, admin, topic, quiz, concept test, programming test, visualization, problem-solving, performance). Each implements the same protocol: `process_request(AgentRequest) → AgentResponse`.
- **Services** (`app/services/`): Shared infrastructure: **ContextStore** (session/conversation/performance state), **LLM provider** (completion API).
- **Config** (`app/config/`): Settings from env, DB/Redis URL building, rate limits, resiliency (retries, circuit breaker).
- **DB/Infra** (`app/db/`, `app/infra/`): Postgres pool, repositories (conversations, jobs), Redis (cache, queues).
- **Utils** (`app/utils/`): Typed errors, ID generation.

**Design patterns in the big picture**

- **Orchestrator**: One component receives all chat requests and delegates to specialists (agents) by intent.
- **Registry**: Intent → agent mapping; agents are registered at startup (wiring), routing only looks up by intent.
- **Dependency injection (DI)**: Routers don’t construct orchestrator or DB; they use FastAPI `Depends(get_orchestrator)` etc., and `deps.py` builds the object graph (with `@lru_cache` singletons).
- **Protocol/interface**: Agents implement `BaseAgent`; context storage implements `ContextStore`; LLM implements `LLMProvider`. This allows swapping implementations (e.g. memory vs Postgres store, no-op vs real tracer) without changing callers.

---

## 2. API Layer

### 2.1 `app/api/main.py`

**What it does**

- Creates the FastAPI app, mounts middleware and routers, and registers exception handlers so domain/application errors become consistent HTTP responses.

**Why it’s written this way**

- **Factory `create_app()`**: So tests can create a fresh app instance without global state. The module also exposes `app = create_app()` for the ASGI server (e.g. uvicorn).
- **Middleware order**: Comment states “last added is innermost (runs first)”. So `add_middleware(Logging)` then `RateLimit` then `CorrelationId` gives order: CorrelationId → RateLimit → Logging when a request comes in. Correlation ID is set first so every other layer can use it.
- **Exception handlers**: Each custom exception (`InvalidSessionError`, `QuizNotFoundError`, etc.) is mapped to a specific status code (400, 404, 429, 504, 500) and a stable `code` field for clients. The generic `EducationError` handler catches LLM/context/orchestrator/agent errors and returns 500 without leaking internals.

**Connections**

- Imports routers from `app.api.routers` and exception classes from `app.utils.errors`. Uses `get_logger` from `app.observability.logging`. Middleware live in `app.api.middleware`.

**Design pattern**

- **Application factory**: `create_app()` returns a configured `FastAPI` instance.
- **Centralized error handling**: All known exceptions are turned into JSON responses with `detail` and `code`.

**If you remove it**

- No FastAPI app: the service doesn’t serve HTTP. Removing only exception handlers would cause unhandled exceptions and 500s without consistent shape.

**Simpler version**

- A minimal version would be a single file that creates `FastAPI()`, adds one router, and has one generic `except Exception` returning 500. The current structure is for multiple routers, clear status codes, and correlation IDs in logs.

---

### 2.2 `app/api/deps.py`

**What it does**

- Provides the **dependency injection** layer: functions that build and return the orchestrator, context store, context manager, agent registry, LLM provider, and specific agents (quiz, concept test, etc.). Used by `Depends(get_orchestrator)` and similar in routers.

**Why it’s written this way**

- **`@lru_cache(maxsize=1)`**: Each getter returns a single shared instance (singleton per process). So all requests share the same orchestrator, context store, and registry. This avoids creating new DB/LLM connections per request.
- **Lazy construction**: e.g. `get_context_store()` reads `settings.context_store_mode` and either returns `MemoryStore()` or builds `PostgresContextStore` with repos from `get_engine()`. So DB is only touched when “persistent” mode is used.
- **Registry as single source of agents**: Assessment and other routers get `QuizAgent` etc. via `get_agent_registry().get_agent(Intent.QUIZ)` so there is one place where agents are created and mapped to intents.

**Connections**

- Uses `app.config.settings`, `app.db.pool.get_engine`, `app.db.repositories.*`, `app.orchestrator.*`, `app.services.context.memory_store` and `postgres_store`, and (lazily) `app.services.llm.openai_provider`. Routers depend on these getters.

**Design pattern**

- **Composition root / DI container**: All wiring (registry, store, tracer, context manager, orchestrator) is done here. **Singleton**: each getter is cached.

**If you remove it**

- Routers would have to instantiate orchestrator and agents themselves, leading to duplicate instances, no shared context store, and harder testing. Removing a single getter (e.g. `get_orchestrator`) would break the router that uses `Depends(get_orchestrator)`.

**Simpler version**

- Global variables created at import time (e.g. `orchestrator = OrchestratorAgent(...)`). That would work for one process but makes tests and configuration changes harder.

---

### 2.3 `app/api/routers/chat.py`

**What it does**

- Exposes `POST /api/v1/chat`: accepts `ChatRequest` (message, session_id, user_id), builds a `UserRequest`, calls `orchestrator.route_request(user_request)`, and returns `ChatResponse` (content, success, metadata, correlation_id).

**Why it’s written this way**

- **Thin router**: No business logic; only (1) map body/headers to `UserRequest`, (2) call orchestrator, (3) map `AgentResponse` to `ChatResponse`. Correlation ID comes from `request.state` (set by middleware).
- **Explicit error handling**: Catches `ValidationError` and `OrchestratorError` to return 400 and 500 with a stable JSON shape, while letting FastAPI send other errors (e.g. 429 from middleware) as usual.

**Connections**

- Depends on `get_orchestrator` from `app.api.deps`. Uses `app.api.schemas.v1.chat` for request/response models and `app.orchestrator.types.UserRequest`. Errors from `app.utils.errors`.

**Design pattern**

- **Thin controller**: Router only handles HTTP; orchestration and domain logic live in the orchestrator and agents.

**If you remove it**

- No `/chat` endpoint; the main student-facing entry point would be gone. Other routers (assessment, visualization, problem_solving) would still work for their own URLs.

**Simpler version**

- A single endpoint that reads `message` from the body, calls one function that returns a string, and returns `{"content": "..."}`. The current version adds session, correlation ID, and structured errors.

---

### 2.4 Middleware: `correlation.py`, `ratelimit.py`, `logging_mw.py`

**What they do**

- **CorrelationIdMiddleware**: Sets `request.state.correlation_id` from header `X-Correlation-ID` or generates a UUID; adds the same ID to the response header. So every request has a trace ID.
- **RateLimitMiddleware**: In-memory per-client (by `X-User-ID` or IP) rate limit; rejects with 429 when over limit within a 1-minute window.
- **LoggingMiddleware**: After `call_next`, logs method, path, status_code, duration_ms, correlation_id.

**Why they’re written this way**

- **BaseHTTPMiddleware**: Standard Starlette/FastAPI way to wrap the request/response. Order of registration determines order of execution (outer vs inner).
- **Correlation first**: So later middleware and the app can always assume `request.state.correlation_id` exists.
- **Rate limit in memory**: Simple and process-local; for multi-instance deployments you’d replace with Redis-backed limits (same interface possible).

**Connections**

- Correlation and logging use `request.state.correlation_id` (set by correlation middleware). Rate limit uses `app.config.limits.rate_limit_config`.

**Design pattern**

- **Pipeline / chain of responsibility**: Request passes through correlation → rate limit → logging → route handler; response passes back through the same chain.

**If you remove one**

- No correlation: logs and error responses lose a consistent request ID. No rate limit: abuse possible. No logging: no request/response audit in one place.

**Simpler version**

- Omit middleware and handle nothing; or a single middleware that only logs “request received” and “response sent” without correlation or rate limiting.

---

## 3. Orchestrator

### 3.1 `app/orchestrator/orchestrator_agent.py`

**What it does**

- **OrchestratorAgent** is the single entry point for chat: validate request, classify intent, load session context, select agent, call agent with timeout, persist user/assistant turn, return one `AgentResponse` (or fallback if intent unknown or no agent).

**Why it’s written this way**

- **Single responsibility**: Orchestration only (classify, route, delegate, persist). It does not implement topic or quiz logic; agents do.
- **Keyword-based classification**: `classify_intent()` uses a fixed list of (Intent, keywords) so that small, predictable phrases map to intents without an LLM call. Order of tuples matters for overlapping keywords (first match wins).
- **Validation and sanitization**: `validate_and_sanitize_request()` rejects empty or overly long messages and returns a sanitized copy so downstream code sees consistent data.
- **Timeout**: `with_timeout(_call_agent(), timeout_seconds=...)` avoids one slow agent blocking the whole API.
- **Context**: Session context is loaded from `ContextStore` and passed in `AgentRequest.context`; after the agent responds, `ContextManager.persist_turn()` appends user and assistant messages so the next request has conversation history.

**Connections**

- Uses `app.orchestrator.policies.with_timeout`, `app.orchestrator.routing.select_agent`, `app.orchestrator.types` (AgentRequest, AgentResponse, Intent, UserRequest), `app.utils.errors`, and (injected) `AgentRegistry`, `ContextStore`, `Tracer`, `ContextManager`.

**Design pattern**

- **Orchestrator**: Central coordinator that delegates to specialists (agents). **Strategy**: Intent determines which agent (strategy) runs.

**If you remove it**

- Chat would have no single place to classify intent and call the right agent; you’d have to duplicate that logic in the router or spread across many endpoints.

**Simpler version**

- A function that only does: if "syllabus" in message then call syllabus_agent else return "I don’t understand." No validation, timeout, context, or persistence.

---

### 3.2 `app/orchestrator/registry.py`

**What it does**

- **AgentRegistry** keeps a mapping `Intent → BaseAgent` and a list of all agents. `register(intent, agent)` sets the agent for that intent; `register_capabilities(agent)` registers the agent for every intent whose name matches one of the agent’s capability strings. `get_agent(intent)` / `select_agent(intent)` return the agent or None. `all_agents()` returns the full list (e.g. for health checks).

**Why it’s written this way**

- **Single place for routing table**: Adding a new agent = register it in wiring; no change to orchestrator routing logic.
- **Capability-based registration**: An agent that handles multiple intents (e.g. performance + assessment) can declare capabilities and be registered for all of them in one call.

**Connections**

- Used by `app.orchestrator.wiring.build_agent_registry()` to populate the registry and by `app.orchestrator.routing.select_agent()` and `OrchestratorAgent.all_agents()`. Types use `app.orchestrator.types.Intent` and `app.agents.base.base_agent.BaseAgent`.

**Design pattern**

- **Registry / service locator**: Look up a handler by key (intent). Not full DI; the wiring module still constructs agents and passes them into the registry.

**If you remove it**

- Orchestrator would have no way to get an agent for an intent; you’d need another mechanism (e.g. a big if/else or a dict built elsewhere).

**Simpler version**

- A global dict `INTENT_AGENTS = {Intent.SYLLABUS: syllabus_agent, ...}` and `select_agent(intent)` returns `INTENT_AGENTS.get(intent)`.

---

### 3.3 `app/orchestrator/routing.py`

**What it does**

- `select_agent(registry, intent)` returns `registry.select_agent(intent)`. So routing is “ask the registry for the agent for this intent.”

**Why it’s written this way**

- Routing logic is one function that delegates to the registry. Extensions (e.g. fallback agent, load balancing) can be added here without touching the orchestrator’s main flow.

**Connections**

- Called by `OrchestratorAgent.route_request()`. Uses `AgentRegistry` and `Intent`.

**Design pattern**

- **Delegation**: Orchestrator doesn’t know how the agent is chosen; it asks the routing module.

**If you remove it**

- Orchestrator would need to call `registry.select_agent(intent)` directly; routing is a thin wrapper, so the only loss is a single place to extend selection logic.

**Simpler version**

- Inline in orchestrator: `agent = registry.get_agent(intent)`.

---

### 3.4 `app/orchestrator/wiring.py`

**What it does**

- **build_agent_registry(llm_provider, context_store)** creates an `AgentRegistry`, instantiates each agent (with optional LLM and context store), and registers them by intent. Assessment-related agents (quiz, concept test, programming test, performance, problem_solving) are only registered when `context_store` is not None.

**Why it’s written this way**

- **Composition root for agents**: All agent construction and dependency passing happens in one place. Context-dependent agents get the same `context_store` and (where needed) shared `PerformanceMonitorAgent` and question banks.
- **Conditional registration**: Without a context store (e.g. minimal config), only stateless agents (syllabus, admin, topic, visualization) are registered; chat still works for those intents.

**Connections**

- Imports all agent classes from `app.agents.*`, shared tools (e.g. `QuestionBank`, `ProgrammingQuestionBank`, `execute_in_docker`), `AgentRegistry`, and `Intent`. Called from `app.api.deps.get_agent_registry()`.

**Design pattern**

- **Factory / composition root**: Builds the full object graph (registry + all agents) from high-level dependencies (LLM, context store).

**If you remove it**

- No central place to create and register agents; deps would have to duplicate agent creation and registration, and consistency (e.g. one shared PerformanceMonitorAgent) would be harder.

**Simpler version**

- In deps: create registry, then manually `registry.register(Intent.SYLLABUS, SyllabusAgent()); ...` for each agent. Wiring just moves that list into a dedicated module.

---

### 3.5 `app/orchestrator/context_manager.py`

**What it does**

- **ContextManager** wraps a `ContextStore` and exposes: `get_session_context`, `get_conversation_history`, `persist_turn`, `set_state`, `set_state_many`, `delete_session`. `persist_turn` appends user and assistant messages; if the store returns an awaitable (e.g. async Postgres), it schedules it and logs success/failure without blocking.

**Why it’s written this way**

- **Facade**: One place for “persist a chat turn” and “get history/context” so the orchestrator doesn’t care whether the store is sync or async. `_maybe_schedule()` handles both sync and async store implementations and avoids blocking the request on async persistence.
- **Structured logging**: Success/failure of persist is logged with session_id, role, correlation_id for debugging.

**Connections**

- Used by `OrchestratorAgent` to persist each turn after routing. Injected with a `ContextStore` from deps. Store protocol in `app.services.context.store`.

**Design pattern**

- **Facade**: Simplifies the store interface for the orchestrator and hides async/sync details.

**If you remove it**

- Orchestrator would call `ContextStore` directly; it would need to handle async append (e.g. create_task or await) and logging itself. Persist logic would be duplicated if another consumer needed it.

**Simpler version**

- Orchestrator calls `store.append_message(session_id, "user", msg)` and `store.append_message(session_id, "assistant", content)` directly and assumes sync; no wrapper.

---

### 3.6 `app/orchestrator/types.py`

**What it does**

- Defines **Intent** (enum of routing targets), **UserRequest** (incoming message, session_id, correlation_id, user_id), **AgentRequest** (message, session_id, correlation_id, intent, context), **AgentResponse** (content, agent_id, success, metadata, error_message), and **AssessmentResult** for performance logging.

**Why it’s written this way**

- **Shared contracts**: All components that pass “user request” or “agent request/response” use the same Pydantic models and enum so that validation and serialization are consistent and type-checkable.
- **Intent as enum**: Prevents typos and allows registry to use intent as key.

**Connections**

- Used by API schemas, orchestrator, routing, registry, wiring, and every agent. Central to the orchestration layer.

**Design pattern**

- **Shared kernel**: Common types for the bounded context (orchestration + agents).

**If you remove it**

- Each layer would define its own request/response shapes; compatibility would break and duplication would grow.

**Simpler version**

- Plain dicts or TypedDicts; you lose validation and clear documentation that Pydantic gives.

---

### 3.7 `app/orchestrator/policies.py`

**What it does**

- **with_timeout(coro, timeout_seconds, timeout_message)**: Runs a coroutine with `asyncio.wait_for`; on timeout raises `app.utils.errors.TimeoutError`.
- **with_retry(fn, ...)**: Runs an async callable with retries and exponential backoff (optional jitter), using `resiliency_config.retries` when args are omitted.
- **CircuitBreaker**: In-memory state machine (closed → open → half_open → closed) to fail fast when a dependency is failing repeatedly.

**Why it’s written this way**

- **Resilience**: Timeout prevents one slow agent from holding the request forever; retry helps with transient failures; circuit breaker prevents hammering a failing service.
- **Config-driven**: Retry and circuit breaker use `app.config.resiliency` so behavior can change without code change.

**Connections**

- Used by `OrchestratorAgent` for `with_timeout` on agent calls. Uses `app.config.resiliency` and `app.utils.errors.TimeoutError`.

**Design pattern**

- **Policies / resilience patterns**: Timeout, retry with backoff, circuit breaker are standard patterns for outbound calls.

**If you remove it**

- Removing timeout: a stuck agent can hang the request indefinitely. Removing retry/circuit breaker: no automatic recovery or protection against cascading failures (depending on where they’re used).

**Simpler version**

- Only `await agent.process_request(...)` with no timeout; no retry or circuit breaker.

---

### 3.8 `app/orchestrator/tracing.py`

**What it does**

- Defines **Tracer** and **Span** protocols and **NoOpTracer** / **NoOpSpan** (no-op implementation) and **ConsoleTracer** / **_ConsoleSpan** (log span start/end and attributes). Supports setting and propagating **correlation_id**.

**Why it’s written this way**

- **Pluggable tracing**: Orchestrator and agents can call `tracer.start_span(...)` and `span.set_attribute(...)`; in production you can swap in an OpenTelemetry tracer without changing orchestrator code.
- **No-op by default**: Tests and minimal setups don’t need a real tracing backend; they use NoOpTracer.

**Connections**

- Orchestrator receives a `Tracer` from deps (currently `NoOpTracer`) and starts a span around the route, sets intent/agent_id, and ends the span in `finally`.

**Design pattern**

- **Strategy / null object**: Tracer is an abstraction; no-op is the null implementation.

**If you remove it**

- No structured spans; you’d rely only on logs. Removing the protocol would force orchestrator to know about a concrete tracer type.

**Simpler version**

- No tracer; orchestrator just logs “start” and “done” with correlation_id.

---

## 4. Agents

### 4.1 `app/agents/base/base_agent.py`

**What it does**

- **BaseAgent** is a **Protocol** (runtime_checkable): `agent_id`, `get_capabilities()`, `process_request(AgentRequest) -> AgentResponse`, `health_check()`.
- **AbstractBaseAgent** is an ABC that implements `agent_id`, `get_capabilities()`, and `health_check()` (default True), and leaves `process_request` abstract so each concrete agent implements it.

**Why it’s written this way**

- **Protocol**: Any class that implements these methods can be used as an agent without inheriting from a base class; the registry and orchestrator depend on the interface, not a specific class.
- **AbstractBaseAgent**: Shared boilerplate (storing agent_id and capabilities) and a single place to add default behavior (e.g. health_check). Concrete agents extend it and implement only `process_request`.

**Connections**

- Every concrete agent (Syllabus, Admin, TopicExpert, Quiz, ConceptTest, ProgrammingTest, Visualization, ProblemSolving, PerformanceMonitor) implements this interface. Orchestrator and registry use `BaseAgent` in type hints.

**Design pattern**

- **Protocol (structural subtyping)** and **Template method** (abstract process_request).

**If you remove it**

- No common contract; registry and orchestrator would have to accept “any object with process_request”. Type checking and refactoring would be harder.

**Simpler version**

- Only a single abstract class with `async def process_request(...)` and no protocol; all agents must inherit that class.

---

### 4.2 `app/agents/information/topic_expert_agent.py` (example agent)

**What it does**

- **TopicExpertAgent** handles intent TOPIC: explains concepts, related topics, and difficulty. If an LLM provider is configured, it uses it for the explanation; otherwise it uses a small in-memory stub KB (`_STUB_CONCEPTS`). Helper functions `_find_concept_key`, `explain_concept_stub`, etc., support the stub path.

**Why it’s written this way**

- **Dependency injection**: Constructor receives optional `llm_provider`; same agent works with or without an LLM (e.g. in tests or when API key is missing).
- **Stub fallback**: When LLM is absent or fails, the stub KB still answers for a few concepts so the product is usable.
- **Single response shape**: Always returns an `AgentResponse` with content, agent_id, success, metadata (intent, correlation_id).

**Connections**

- Built in `app.orchestrator.wiring` with `llm_provider=get_llm_provider()`. Uses `app.orchestrator.types.AgentRequest`, `AgentResponse`, `Intent`. Uses `app.services.llm.provider.LLMProvider` when present.

**Design pattern**

- **Strategy**: LLM vs stub is a strategy for “how to generate the answer.” **Adapter**: Agent adapts the LLM completion API to the `AgentResponse` contract.

**If you remove it**

- TOPIC intent would have no handler; orchestrator would fall back to “I didn’t quite understand that” for topic questions.

**Simpler version**

- A function that takes a string and returns a fixed string (e.g. “This is a topic question”) with no LLM, no stub KB, and no AgentResponse.

---

## 5. Services

### 5.1 `app/services/context/store.py`

**What it does**

- Defines the **ContextStore** **Protocol**: `get`, `set`, `set_many`, `append_message`, `get_history`, `delete`, plus assessment-related `append_assessment_result`, `get_performance_summary`, `update_summary`. Docstring describes session state key conventions (e.g. `programming_test:state`, `problem_solving:state`).

**Why it’s written this way**

- **Interface only**: No implementation here; implementations (MemoryStore, PostgresContextStore) live elsewhere. This allows swapping storage without changing orchestrator or agents that depend on ContextStore.
- **Single place for contract**: All consumers (orchestrator, context manager, agents) depend on this protocol.

**Connections**

- Implemented by `app.services.context.memory_store.MemoryStore` and `app.services.context.postgres_store.PostgresContextStore`. Used by `ContextManager`, `deps.get_context_store()`, and agents that need session/performance data.

**Design pattern**

- **Protocol (interface)** and **Repository**-style abstraction over “session and conversation store.”

**If you remove it**

- Callers would depend on concrete store classes; switching to Postgres or another backend would require changing many files.

**Simpler version**

- A single concrete class (e.g. only MemoryStore) and no protocol; code would call that class directly.

---

### 5.2 `app/services/context/memory_store.py`

**What it does**

- **MemoryStore** implements ContextStore in process memory: dicts for sessions, history, performance metrics, and performance summary. Implements `update_summary()` by computing avg_score, weak/strong topics, and alert_flag from recent results.

**Why it’s written this way**

- **Default for dev/tests**: No DB or Redis required; works out of the box when `context_store_mode != "persistent"`.
- **Same contract as protocol**: So orchestrator and agents don’t care whether they’re talking to MemoryStore or PostgresContextStore.

**Connections**

- Used by `deps.get_context_store()` when mode is not `"persistent"`. Implements `ContextStore` from `app.services.context.store`.

**Design pattern**

- **Concrete implementation** of the ContextStore protocol; **in-memory repository**.

**If you remove it**

- You’d need another default implementation (e.g. always Postgres) or the app would fail when context store is requested without Postgres.

**Simpler version**

- Only `get`/`set` for a flat session dict, no history or performance methods.

---

### 5.3 `app/services/llm/provider.py`

**What it does**

- Defines the **LLMProvider** **Protocol**: async `complete(prompt, *, model, temperature, timeout_seconds)` returning `str`. Documents that it may raise `LLMProviderError` and `TimeoutError`.

**Why it’s written this way**

- **Single interface for LLM calls**: Agents that need an LLM (TopicExpert, ConceptTest, Visualization, ProblemSolving, etc.) depend on this protocol, not on OpenAI or a specific SDK. You can add another provider (e.g. Anthropic) by implementing the same protocol.
- **Protocol**: Allows any implementation to be passed in (e.g. OpenAIProvider in production, mock in tests).

**Connections**

- Implemented by `app.services.llm.openai_provider` (and potentially others). Injected into agents by `app.orchestrator.wiring.build_agent_registry(llm_provider=...)`.

**Design pattern**

- **Port** (interface) for the “LLM completion” capability; **adapter** for each provider.

**If you remove it**

- Agents would call OpenAI (or similar) directly; switching provider or mocking in tests would require touching every agent that uses the LLM.

**Simpler version**

- No protocol; each agent imports and uses one concrete LLM client.

---

## 6. Config and Infrastructure

### 6.1 `app/config/settings.py`

**What it does**

- **Settings** (Pydantic BaseSettings) loads configuration from the environment (and `.env`): app env, port, queues, context_store_mode, database_url, Postgres/Redis params, vector DB, LLM provider/key/model, storage, auth, telemetry. A global `settings` instance is created at import time.

**Why it’s written this way**

- **Twelve-factor**: Config from environment so the same code can run in dev/staging/production with different env files or env vars.
- **Pydantic**: Validates types and gives one place to document and default every variable. `extra="ignore"` avoids errors on unknown env vars.

**Connections**

- Used by `app.api.deps`, `app.config.db_redis`, `app.config.limits`, `app.config.resiliency`, and anywhere that needs app/config values.

**Design pattern**

- **Configuration object**: Single object holding all settings.

**If you remove it**

- Every module would read `os.environ` itself; defaults and validation would be scattered and inconsistent.

**Simpler version**

- A module with constants like `PORT = int(os.environ.get("PORT", "8000"))` and no Pydantic.

---

### 6.2 `app/config/db_redis.py`

**What it does**

- Builds Postgres URL (`build_postgres_url()`), Postgres pool options (`postgres_pool_options()`), Redis URLs for cache and queues (`build_redis_cache_url()`, `build_redis_queues_url()`), and Redis pool options (`redis_pool_options()`). Single place that reads `settings` and produces URLs and pool config.

**Why it’s written this way**

- **Single source of truth**: All DB/Redis connection parameters come from settings and are assembled here, so `app.db.pool` and Redis clients don’t duplicate URL logic.
- **Async driver**: Postgres URL uses `postgresql+asyncpg://` so it’s suitable for SQLAlchemy async engine.

**Connections**

- Used by `app.db.pool` and Redis-related code in `app.infra.redis`. Uses `app.config.settings`.

**Design pattern**

- **Factory** for connection configuration (URLs and pool options).

**If you remove it**

- Each consumer would build its own URL from settings; if the URL format or driver changed, you’d update multiple places.

**Simpler version**

- One function that returns `settings.database_url` and no granular Postgres/Redis helpers.

---

### 6.3 `app/db/pool.py`

**What it does**

- **get_engine()** returns a process-wide async SQLAlchemy engine (lazy-created from `db_redis.build_postgres_url()` and pool options). **dispose_engine()** disposes it (e.g. on shutdown or in tests).

**Why it’s written this way**

- **Single pool per process**: Avoids opening many connections; reuse is efficient. Lazy creation means no DB connection if the app never uses Postgres (e.g. memory-only context store).
- **pool_pre_ping**: Checks connections before use so stale connections are dropped.

**Connections**

- Used by `app.api.deps` when building `PostgresContextStore` (and by repos). Uses `app.config.db_redis`.

**Design pattern**

- **Singleton** (module-level engine) with **lazy initialization**.

**If you remove it**

- Every consumer would create its own engine; connection count could grow and configuration would be duplicated.

**Simpler version**

- Create the engine once at import and export it; no dispose. Simpler but harder to test and shut down cleanly.

---

## 7. Utils and Errors

### 7.1 `app/utils/errors.py`

**What it does**

- Defines a hierarchy of exceptions: **EducationError** (base with `message`, `code`), then **AgentError**, **OrchestratorError**, **LLMProviderError**, **ContextStoreError**, **ValidationError**, **RateLimitError**, **TimeoutError**, **QuizNotFoundError**, **TestAlreadyCompleteError**, **InvalidSessionError**.

**Why it’s written this way**

- **Stable error codes**: Handlers in `main.py` map each type to an HTTP status and attach a `code` so clients can handle errors programmatically.
- **Hierarchy**: Catch `EducationError` for “any app error” and more specific types when you need different handling (e.g. 400 for ValidationError, 429 for RateLimitError).

**Connections**

- Raised by orchestrator, agents, middleware, and config/policies. Caught in `app.api.main` exception handlers.

**Design pattern**

- **Custom exception hierarchy** for domain and infrastructure errors.

**If you remove it**

- Handlers in main would have nothing to catch; you’d use generic `Exception` and lose the ability to return 400/404/429/504 consistently.

**Simpler version**

- One exception class `AppError(message, code)` and no subclasses; handlers would branch on `code` only.

---

## 8. Summary Diagram (component relationships)

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                      main.py (create_app)                │
                    │  Middleware: CorrelationId → RateLimit → Logging         │
                    │  Routers: health, chat, assessment, visualization,       │
                    │           problem_solving                                │
                    │  Exception handlers → JSONResponse(status_code, detail)  │
                    └───────────────────────────┬──────────────────────────────┘
                                                │
                    ┌───────────────────────────▼──────────────────────────────┐
                    │                      deps.py                             │
                    │  get_context_store() → MemoryStore | PostgresContextStore │
                    │  get_llm_provider() → OpenAIProvider | None               │
                    │  get_context_manager() → ContextManager(store)             │
                    │  get_agent_registry() → build_agent_registry(...)         │
                    │  get_orchestrator() → OrchestratorAgent(registry, ...)    │
                    └───────────────────────────┬──────────────────────────────┘
                                                │
        ┌───────────────────────────────────────┼───────────────────────────────────────┐
        │                                       │                                       │
        ▼                                       ▼                                       ▼
┌───────────────┐                    ┌──────────────────────┐                 ┌─────────────────┐
│ chat router   │                    │ OrchestratorAgent    │                 │ assessment etc. │
│ POST /chat    │───────────────────▶│ route_request()     │                 │ (quiz, concept, │
│               │  UserRequest       │  classify_intent()   │                 │  programming)   │
└───────────────┘                    │  select_agent()     │                 └────────┬────────┘
                                     │  context_store.get()│                           │
                                     │  agent.process_    │                           │ get_agent(Intent)
                                     │    request()       │◀──────────────────────────┘
                                     │  context_manager.  │
                                     │    persist_turn()  │
                                     └─────────┬──────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌───────────────┐          ┌───────────────┐          ┌───────────────┐
            │ AgentRegistry │          │ ContextStore  │          │ ContextManager│
            │ intent→agent  │          │ (memory /     │          │ persist_turn  │
            │ all_agents()  │          │  postgres)    │          │ get_history   │
            └───────┬───────┘          └───────────────┘          └───────────────┘
                    │
                    │ wiring builds: SyllabusAgent, AdministrationAgent, TopicExpertAgent,
                    │ QuizAgent, ConceptTestAgent, ProgrammingTestAgent, VisualizationAgent,
                    │ ProblemSolvingAgent, PerformanceMonitorAgent
                    ▼
            ┌───────────────┐
            │ BaseAgent     │  agent_id, get_capabilities(), process_request(), health_check()
            │ (Protocol)    │
            └───────────────┘
```

---

This guide should give you a clear picture of what each file and layer does, why it’s structured that way, how it connects to the rest of the system, which patterns are used, what breaks if something is removed, and what a minimal version would look like. Use it as a map when reading or changing the codebase.
