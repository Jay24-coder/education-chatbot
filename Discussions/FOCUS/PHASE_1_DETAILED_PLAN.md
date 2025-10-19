# Phase 1: Foundation Implementation Plan
*Weeks 1-2*

## Overview
Phase 1 focuses on establishing the foundational multi-agent framework using LangGraph and implementing the core orchestration system with basic information agents.

## Core Objectives
1. Set up basic LangGraph multi-agent framework
2. Implement Orchestrator Agent with basic routing
3. Create simple Information Agents (Syllabus, Admin, Topic)

## Detailed Implementation Tasks

### 1. Project Setup & Dependencies (Week 1, Days 1-2)

#### 1.1 Environment Setup
- [ ] Verify LangGraph installation in `pyproject.toml`
- [ ] Set up virtual environment with proper Python version
- [ ] Install additional required dependencies:
  - `langchain` - Agent building and tool integration
  - `fastapi` - REST API framework
  - `uvicorn` - ASGI server
  - `pydantic` - Data validation
  - `python-dotenv` - Environment variable management

#### 1.2 Project Structure
- [ ] Create directory structure:
  ```
  /agents/
    /orchestrator/
    /information/
    /shared/
  /models/
  /utils/
  /api/
  /tests/
  ```

#### 1.3 Configuration Management
- [ ] Set up environment configuration files
- [ ] Create base configuration classes
- [ ] Implement logging setup

### 2. LangGraph Multi-Agent Framework Setup (Week 1, Days 3-4)

#### 2.1 Core Framework Implementation
- [ ] Create base agent class with common functionality
- [ ] Implement agent registry system
- [ ] Set up inter-agent communication protocols
- [ ] Create shared state management system

#### 2.2 Agent Lifecycle Management
- [ ] Implement agent initialization
- [ ] Create agent health monitoring
- [ ] Set up graceful shutdown procedures

### 3. Orchestrator Agent Implementation (Week 1, Days 5-7)

#### 3.1 Request Classification System
- [ ] Implement intent classification using NLP
- [ ] Create request routing logic
- [ ] Build fallback handling for ambiguous requests
- [ ] Add request validation and sanitization

#### 3.2 Agent Selection & Coordination
- [ ] Develop agent selection algorithm
- [ ] Implement response aggregation system
- [ ] Create error handling and retry mechanisms
- [ ] Add performance monitoring hooks

#### 3.3 Orchestrator Core Features
- [ ] Request preprocessing
- [ ] Agent delegation
- [ ] Response post-processing
- [ ] Context management integration

### 4. Information Agents Development (Week 2, Days 1-4)

#### 4.1 Syllabus Agent
- [ ] Create curriculum data structure
- [ ] Implement course structure queries
- [ ] Add prerequisite checking functionality
- [ ] Build syllabus search and filtering

**Key Capabilities:**
- Handle curriculum queries
- Course structure information
- Prerequisites management
- Academic calendar integration

#### 4.2 Administration Agent
- [ ] Set up institutional policy database
- [ ] Implement procedure lookup system
- [ ] Create deadline tracking functionality
- [ ] Add policy explanation capabilities

**Key Capabilities:**
- Institutional policies
- Administrative procedures
- Deadline management
- Policy clarification

#### 4.3 Topic Expert Agent
- [ ] Create subject knowledge base
- [ ] Implement concept explanation system
- [ ] Add topic relationship mapping
- [ ] Build difficulty level assessment

**Key Capabilities:**
- Detailed subject explanations
- Concept relationships
- Difficulty progression
- Learning path recommendations

### 5. Shared Services Implementation (Week 2, Days 5-7)

#### 5.1 Context Manager Agent
- [ ] Implement student state management
- [ ] Create conversation history tracking
- [ ] Add session persistence
- [ ] Build context retrieval system

#### 5.2 Basic Knowledge Base
- [ ] Set up curriculum content storage
- [ ] Implement content indexing
- [ ] Create search functionality
- [ ] Add content versioning

#### 5.3 Communication Layer
- [ ] Implement REST API endpoints
- [ ] Create WebSocket support for real-time communication
- [ ] Add request/response logging
- [ ] Implement rate limiting

## Technical Implementation Details

### Core Dependencies Required
```toml
[dependencies]
langgraph = "^0.0.40"
langchain = "^0.1.0"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
pydantic = "^2.5.0"
python-dotenv = "^1.0.0"
```

### Key Classes to Implement

#### 1. BaseAgent Class
```python
class BaseAgent:
    def __init__(self, agent_id: str, capabilities: List[str])
    async def process_request(self, request: AgentRequest) -> AgentResponse
    def get_capabilities(self) -> List[str]
    def health_check(self) -> bool
```

#### 2. OrchestratorAgent Class
```python
class OrchestratorAgent(BaseAgent):
    def __init__(self)
    async def route_request(self, request: UserRequest) -> AgentResponse
    def select_agent(self, intent: str) -> BaseAgent
    async def aggregate_responses(self, responses: List[AgentResponse]) -> AgentResponse
```

#### 3. Information Agent Classes
```python
class SyllabusAgent(BaseAgent):
    async def get_course_info(self, course_id: str) -> CourseInfo
    async def get_prerequisites(self, course_id: str) -> List[str]
    async def search_syllabus(self, query: str) -> List[SyllabusItem]

class AdministrationAgent(BaseAgent):
    async def get_policy(self, policy_type: str) -> Policy
    async def get_deadlines(self, student_id: str) -> List[Deadline]
    async def explain_procedure(self, procedure: str) -> str

class TopicExpertAgent(BaseAgent):
    async def explain_concept(self, topic: str, level: str) -> str
    async def get_related_topics(self, topic: str) -> List[str]
    async def assess_difficulty(self, topic: str) -> DifficultyLevel
```

## Testing Strategy

### Unit Tests
- [ ] Test individual agent functionality
- [ ] Test orchestrator routing logic
- [ ] Test request/response handling
- [ ] Test error scenarios

### Integration Tests
- [ ] Test agent-to-agent communication
- [ ] Test end-to-end request flow
- [ ] Test context management
- [ ] Test API endpoints

### Performance Tests
- [ ] Load testing for concurrent requests
- [ ] Memory usage monitoring
- [ ] Response time benchmarks

## Success Criteria

### Functional Requirements
- [ ] Orchestrator can successfully route requests to appropriate agents
- [ ] Information agents can handle basic queries in their domains
- [ ] System can maintain conversation context
- [ ] API endpoints respond correctly to requests

### Non-Functional Requirements
- [ ] Response time < 2 seconds for simple queries
- [ ] System can handle 10+ concurrent users
- [ ] 99% uptime during testing
- [ ] Proper error handling and logging

## Deliverables

### Code Deliverables
1. **Core Framework**
   - Base agent implementation
   - Orchestrator agent with routing
   - Three information agents (Syllabus, Admin, Topic)
   - Context manager
   - Basic API endpoints

2. **Documentation**
   - API documentation
   - Agent interaction diagrams
   - Setup and deployment guide
   - Testing documentation

3. **Configuration**
   - Environment setup scripts
   - Docker configuration (optional)
   - Database schema (if needed)

### Demo Capabilities
By end of Phase 1, the system should be able to:
- Accept user requests via API
- Route requests to appropriate agents
- Provide basic syllabus information
- Answer administrative queries
- Explain simple topics
- Maintain conversation context

## Risk Mitigation

### Technical Risks
- **LangGraph Learning Curve**: Allocate extra time for framework understanding
- **Agent Communication**: Start with simple synchronous communication
- **Performance**: Implement basic caching from the start

### Timeline Risks
- **Scope Creep**: Stick strictly to Phase 1 requirements
- **Integration Issues**: Test integration early and often
- **Dependency Issues**: Verify all dependencies work together

## Phase 1.5: Scale-Readiness Checklist

### Checklist (add during Phase 1 where noted)
- [ ] Make agents and orchestrator stateless; move state to external stores
- [ ] Introduce correlation/request IDs in all requests and logs
- [ ] Add timeouts, retries with jitter, and circuit breakers to outbound calls
- [ ] Implement basic rate limiting and per-user quotas
- [ ] Add observability: structured logs, metrics, and tracing spans per agent
- [ ] Use async I/O for all network and disk operations
- [ ] Prepare cache layers for syllabus/policy lookups (Redis)
- [ ] Externalize context/session to Redis; durable data to Postgres
- [ ] Add vector store for retrieval (pgvector/Qdrant) for knowledge queries
- [ ] Define idempotency keys and deduplication for fan-out/queued work
- [ ] Version Pydantic request/response schemas for forward compatibility
- [ ] Containerize services and document horizontal scaling strategy

### Minimal Infra Choices (initially optional, easy to add)
- **In-memory to external**: Start with Redis + Postgres when feasible
- **Vector DB**: pgvector (in Postgres) or Qdrant for embeddings
- **Message/queue**: Redis Streams/RabbitMQ for long-running or fan-out flows
- **Tracing**: OpenTelemetry exporters (console first, backend later)

### Lightweight Interface Notes

These interfaces keep the system modular and swap-friendly without over-engineering Phase 1.

```python
# LLMProvider abstraction: swap models/providers, centralize policies/timeouts
from typing import Protocol, Dict, Any

class LLMProvider(Protocol):
    async def complete(self, prompt: str, *, model: str | None = None, 
                       temperature: float = 0.2, timeout_s: float = 15.0, 
                       metadata: Dict[str, Any] | None = None) -> str:
        ...


# Tracing interface: add spans without hard-coupling to a vendor
class Tracer(Protocol):
    def start_span(self, name: str, **attrs: Any):
        ...
    def end_span(self, error: Exception | None = None):
        ...


# Context store: keep agents stateless and externalize session/conversation
class ContextStore(Protocol):
    async def get_session(self, session_id: str) -> Dict[str, Any] | None:
        ...
    async def set_session(self, session_id: str, data: Dict[str, Any], ttl_s: int | None = None) -> None:
        ...
    async def append_history(self, session_id: str, message: Dict[str, Any]) -> None:
        ...
```

Implementation notes for Phase 1:
- Provide minimal concrete implementations (e.g., Redis-backed `ContextStore`, basic console `Tracer`, single provider `LLMProvider`).
- Wire request IDs through orchestrator → agents; include in logs/metrics/traces.
- Wrap all outbound calls with timeouts and retries; add circuit breaker at orchestrator boundary.

### Architecture: Stateless Services & Horizontal Scaling
- [ ] Run multiple API/orchestrator instances behind a load balancer
- [ ] Ensure `BaseAgent` and `OrchestratorAgent` remain stateless
- [ ] Externalize all stateful concerns to dedicated services (context, caches, DBs)
- [ ] Document autoscaling policies (CPU, memory, p95 latency triggers)

### State & Context Externalization
- [ ] Store conversational context and sessions in Redis
- [ ] Persist durable knowledge and admin data in Postgres
- [ ] Use typed `ContextStore` methods to ensure schema stability
- [ ] Add TTL for ephemeral keys; cleanup policies for stale sessions

### Async Orchestration & Queues
- [ ] Prefer async I/O throughout agents and orchestrator
- [ ] Introduce a queue (Redis Streams/RabbitMQ) for long-running or fan-out tasks
- [ ] Define idempotency keys and deduplication strategy for queued work
- [ ] Implement saga/compensation hooks for multi-step operations

### Resilience & Fault Tolerance
- [ ] Timeouts and retry with jitter for all outbound calls
- [ ] Circuit breakers per dependency (LLM, DB, vector store)
- [ ] Bulkheads: isolate resource pools per agent type where feasible
- [ ] Backpressure: shed load gracefully when saturated
- [ ] Fallback responses for degraded modes in orchestrator

### Caching Strategy
- [ ] Cache syllabus/policy lookups in Redis with sensible TTLs
- [ ] Cache LLM intermediate results where deterministic (e.g., tool schemas)
- [ ] Cache embeddings or retrieval results for hot queries
- [ ] Define cache invalidation rules tied to content versioning

### Model/Provider Abstraction
- [ ] Implement `LLMProvider` interface and one concrete provider to start
- [ ] Centralize model selection, safety settings, and cost/latency policies
- [ ] Support provider failover and feature flags for rollout/shadowing

### Observability
- [ ] Structured logging with request/correlation IDs
- [ ] Metrics: latency, error rate, token usage, queue depth, cache hit rate
- [ ] Tracing: per-request spans across orchestrator and agents (OpenTelemetry)
- [ ] Dashboards and alerts for SLOs (p95 latency, error budgets)

### API Safety & Governance
- [ ] Rate limiting and quotas per user/tenant
- [ ] Schema versioning for Pydantic request/response models
- [ ] Input validation and sanitization on all entry points
- [ ] Audit logs for administrative actions

### Multi-Tenancy
- [ ] Propagate tenant IDs through context and storage layers
- [ ] Choose partitioning: schema-per-tenant or row-level with RLS
- [ ] Isolate rate limits and quotas per tenant
- [ ] Optional: per-tenant encryption keys and data residency constraints

### Delivery & Infrastructure
- [ ] Containerize services; pin base images and dependencies
- [ ] Use Gunicorn + Uvicorn workers; tune worker count per CPU
- [ ] Define health checks, readiness, and liveness probes
- [ ] CI/CD with canary/shadow deployments via feature flags

### Minimal Phase 1 Adjustments (Do Now)
- [ ] Define strict Pydantic models for all agent I/O
- [ ] Add correlation/request IDs and wire through logs/traces
- [ ] Wrap LLM calls with timeouts/retries via `LLMProvider`
- [ ] Keep agent methods pure/async; side effects via `ContextStore`
- [ ] Add basic rate limiting middleware and per-user quotas
- [ ] Prepare a small vector store for retrieval (pgvector/Qdrant)

## Next Phase Preparation

### Phase 2 Readiness
- [ ] Performance monitoring hooks in place
- [ ] Extensible agent architecture
- [ ] Basic assessment framework structure
- [ ] Student profile system foundation

This Phase 1 implementation will provide a solid foundation for the more complex assessment and specialized agents in subsequent phases.
