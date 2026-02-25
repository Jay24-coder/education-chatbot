## Phase 3 Execution Plan (Production-Ready)

This is a concrete, step-by-step execution plan for Phase 3, assuming:

- Programming Test Agent uses a **Docker-based sandbox**.
- We follow existing patterns from Phases 1–2 (orchestrator, DI in `deps.py`, `ContextStore`, `PerformanceMonitorAgent`).

Reasoning: ordering work to finish lowest-risk, highest-leverage pieces first (programming test), then visualization, then the complex image-based problem-solving.

---

### 1. Programming Test Agent with Docker Sandbox

#### 1.1 Design contracts and data models

1. **Define challenge model and results shapes.**
  - Add `ProgrammingChallenge` and `TestCase` models in `app/agents/shared_tools/programming_bank.py`.  
  - Decide fields now: `id`, `title`, `description`, `function_signature`, `language`, `difficulty`, `topic`, `test_cases`.  
  - Define `TestCaseResult` and `ExecutionResult` dataclasses (or typed dicts) in `test_case_runner.py` / `code_execution.py`.  
   Reasoning: a clear model prevents later refactors when wiring agents, API, and tests.
2. **Extend assessment schemas.**
  - In `app/api/schemas/v1/assessment.py` add:
    - `ProgrammingTestStartRequest` (session_id, user_id, optional topic, optional language).  
    - `ProgrammingTestSubmitRequest` (session_id, user_id, code).  
    - `ProgrammingTestResponse` (content, success, metadata, completed, per-test-case results).  
     Reasoning: mirror existing Quiz/ConceptTest patterns so routers stay consistent.

#### 1.2 Docker sandbox design (no code yet)

1. **Decide Docker image and restrictions.**
  - Choose a base image (e.g. `python:3.13-slim`) for code execution.  
  - Decide allowed language(s) for Phase 3 (start with Python only).  
  - Specify resource limits: CPU, memory, max runtime, no network.  
   Reasoning: fixing sandbox constraints now avoids leaky or insecure defaults.
2. **Define sandbox interface.**
  - In `app/agents/shared_tools/code_execution.py`, design the function signature only:  
    - `async def execute_in_docker(code: str, language: str, timeout_seconds: float) -> ExecutionResult`.
  - Decide how to map `ExecutionResult` to `TestCaseResult` (success flag, stdout, stderr, error type).  
   Reasoning: the agent and test runner can be written against this contract before implementing Docker details.

#### 1.3 Implement Docker executor

1. **Implement Docker execution wrapper.**
  - Implement `execute_in_docker` using `docker` CLI or SDK (whichever you prefer for this project).  
  - Behavior:  
    - Build or reuse a minimal image (containing Python and nothing else needed).  
    - For each call: run a short-lived container with the student code mounted or sent as a file, execute, capture stdout/stderr, enforce timeout and resource limits.
  - Raise well-typed errors: `UnsafeCodeError`, `CodeExecutionTimeoutError`, `SandboxError`.  
   Reasoning: a single, well-tested executor isolates all Docker complexity from the agent.
2. **Unit-test the executor in isolation.**
  - `app/tests/unit/test_code_execution.py`:  
    - Simple “hello world” passes.  
    - Infinite loop triggers `CodeExecutionTimeoutError`.  
    - Obvious unsafe code patterns return `UnsafeCodeError` (if you implement a pre-check).  
     Reasoning: catching sandbox issues here prevents noisy failures later in agent tests.

#### 1.4 Implement test-case runner and question bank

1. **Implement `test_case_runner.py`.**
  - Function: `async def run_test_cases(challenge, code, executor) -> list[TestCaseResult]`.  
  - For each test case, call `execute_in_docker`, compare actual vs expected, set `passed` and capture messages.  
   Reasoning: keeps the agent slim and focuses it on orchestration, not low-level execution loops.
2. **Seed `programming_bank.py` with initial challenges.**
  - Start with 3–5 carefully chosen Python problems (arrays, strings, simple math).  
  - Include at least 3–5 test cases per problem, including edge cases.  
  - Add helper: `get_challenge(topic: str | None, difficulty: str | None) -> ProgrammingChallenge`.  
   Reasoning: real, deterministic test cases are critical for reliable evaluation and integration tests.

#### 1.5 Implement Programming Test Agent

1. **Add new intent and wiring.**
  - In `app/orchestrator/types.py`, add `Intent.PROGRAMMING_TEST`.  
  - In `app/orchestrator/orchestrator_agent.py`, extend `_INTENT_KEYWORDS` with phrases like “programming test”, “coding challenge”, “code test”.  
  - In `app/orchestrator/wiring.py`, instantiate `ProgrammingTestAgent` with:
    - `ContextStore`, `ProgrammingQuestionBank`, `PerformanceMonitorAgent`, and the Docker executor.  
     Reasoning: wiring via the existing registry pattern keeps orchestration consistent.
2. **Implement `ProgrammingTestAgent`.**
  - File: `app/agents/assessment/programming_test_agent.py`.  
    - Responsibilities:  
      - `start_test(session_id, message, context)`  
        - Choose challenge via `programming_bank`.  
        - Store under `programming_test:state` in `ContextStore`.  
        - Return challenge description, function signature, and submission instructions.
      - `submit_code(session_id, code, context)`  
        - Load state; if missing, return error.  
        - Use `run_test_cases` to evaluate code.  
        - Compute normalized score (passed/total).  
        - Log via `PerformanceMonitorAgent.append_assessment_result` with `type="programming_test"`.  
        - Return detailed feedback and a `completed` flag.  
        Reasoning: mirrors Quiz/ConceptTest agents, minimizing new patterns.

#### 1.6 API integration and tests

1. **Extend `assessment.py` router.**
  - Add:  
    - `POST /assessment/programming-test/start` → uses `get_programming_test_agent()`.  
    - `POST /assessment/programming-test/submit`.  
    - Map the custom sandbox errors to HTTP status codes (400/503 or similar).  
    Reasoning: keeps all assessments under a single router, matching Phase 2.
2. **Write unit tests for the agent.**
  - `app/tests/unit/test_agent_programming_test.py`:  
    - Mock the Docker executor + question bank.  
    - Test: start → submit (all tests pass, some fail, missing state, etc.).  
    Reasoning: ensure agent logic is correct independent of Docker and HTTP.
3. **Write integration tests for the full flow.**
  - `app/tests/integration/test_programming_test_flow.py`:  
    - Hit `/assessment/programming-test/start`, then `/assessment/programming-test/submit`.  
    - Verify response structure, scoring, and that performance summary reflects results.  
    Reasoning: validates the full path from API → agent → Docker → performance monitor.

---

### 2. Visualization Agent

#### 2.1 Intent and wiring

1. **Add visualization intent.**
  - In `app/orchestrator/types.py`, add `Intent.VISUALIZATION`.  
    - Extend `_INTENT_KEYWORDS` with “draw”, “visualize”, “diagram”, “graph of”, “plot”.  
    - In `wiring.py`, instantiate `VisualizationAgent` with `LLMProvider`.  
    Reasoning: keeps visualization reachable from chat without a separate gateway.

#### 2.2 Agent behavior

1. **Implement `VisualizationAgent`.**
  - File: `app/agents/specialized/visualization_agent.py`.  
    - Behavior:  
      - Classify request as “diagram” (Mermaid) or “graph” (chart spec).  
      - For diagrams: return a ````mermaid ... ```` block plus short explanation.  
      - For graphs: return JSON-like chart spec in `metadata` and a brief explanation in `content`.  
      Reasoning: client can render these with minimal backend complexity.
2. **(Optional) Add `/visualization/generate` router.**
  - In `app/api/routers/visualization.py`, implement a single POST endpoint that accepts a description and desired output type, calls `VisualizationAgent`, and returns structured fields.  
  Reasoning: useful for non-chat consumers (dashboards, tools) but optional if chat is primary.
3. **Tests.**
  - Unit: `test_agent_visualization.py` with LLM mocked:
    - Diagram request → Mermaid output.  
    - Graph request → chart spec.  
    - Integration: small tests via chat (or `/visualization/generate` if added) to verify formats.  
    Reasoning: ensures downstream rendering won’t break due to malformed specs.

---

### 3. Problem-Solving Agent (Image + Guardrails)

#### 3.1 Vision/OCR foundation

1. **Implement OCR / vision utilities.**
  - File: `app/agents/shared_tools/vision.py` and/or `app/agents/problem_solving/image_processor.py`.  
    - Responsibilities:
      - Accept image (bytes/path) and return extracted text plus optional structured hints (equations, symbols).  
      - Use `pytesseract` + OpenCV/Pillow or a cloud Vision API.  
      Reasoning: clean separation lets you mock this for tests and swap providers later.
2. **Unit-test image processing.**
  - `test_image_processor.py`:  
    - Use 1–2 small synthetic images or stubs to verify OCR plumbing and error handling.  
    Reasoning: makes sure bad images fail gracefully before agent logic.

#### 3.2 Guardrail state machine

1. **Implement guardrail logic as pure functions.**
  - File: `app/agents/problem_solving/guardrails.py`.  
    - Define:
      - State model (stage, attempts, confidence flags, topic, difficulty).  
      - `next_state(current_state, student_input, analysis) -> new_state + action`.
    - `analysis` can be a small struct summarizing LLM judgments (e.g. understanding: weak/partial/strong).  
    Reasoning: pure, side-effect-free logic is easy to test and reason about.
2. **Write thorough unit tests for guardrails.**
  - `test_guardrails.py`:  
    - Starting from no state → expects PROBE/ASSESS.  
    - Weak understanding → stays in EXPLAIN_CONCEPT / SIMILAR_PROBLEM.  
    - Strong understanding → progresses to SOLVE.  
    Reasoning: guarantees educational behavior regardless of LLM variance.

#### 3.3 Agent and router

1. **Implement `ProblemSolvingAgent`.**
  - File: `app/agents/specialized/problem_solving_agent.py`.  
    - Responsibilities:
      - First turn:
        - Use image processor to get OCR + coarse classification.  
        - Initialize state and call guardrails to determine first response.
      - Subsequent turns:
        - Load state from `ContextStore` (`problem_solving:state`).  
        - Incorporate latest student reply, call guardrails, and update.
      - Delegate pure text generation to LLM (concepts, hints, similar problems, solution).  
      - Optionally log an assessment-like result when solution is finally shown.  
      Reasoning: centralizes orchestration, but keeps OCR and policies modular.
2. **Add dedicated problem-solving router.**
  - File: `app/api/routers/problem_solving.py`.  
    - Endpoints:
      - `POST /problem-solving/start` (multipart or JSON with image + optional message).  
      - `POST /problem-solving/respond` (session_id, user_id, text answer).
    - Use `get_problem_solving_agent()` directly rather than going through the generic chat endpoint.  
    Reasoning: keeps file uploads and large payloads out of the simple chat flow.
3. **Tests.**
  - Unit:
    - `test_agent_problem_solving.py` with OCR + LLM mocked:
      - Path where solution is withheld due to weak understanding.  
      - Path where hints lead to solution.
    - Integration:
      - `test_problem_solving_flow.py`: start with a test image (or stub), simulate 2–3 turns, and verify state progression.  
      Reasoning: ensures the end-to-end behavior matches the guardrail design.

---

### 4. Orchestrator, Context, and Errors (Cross-Cutting)

1. **Update orchestrator types and wiring once, after agents are implemented.**
  - Add new intents (`PROGRAMMING_TEST`, `VISUALIZATION`, `PROBLEM_SOLVING`).  
    - Register all new agents in `wiring.py`.  
    - Extend `_INTENT_KEYWORDS` thoughtfully to avoid misclassification.  
    Reasoning: doing this after agents exist avoids dangling registrations and half-wired code.
2. **Context store conventions.**
  - Decide and document key names/shapes:
    - `programming_test:state` → challenge id, language, started_at.  
    - `problem_solving:state` → stage, topic, difficulty, attempts.  
    - Use existing `get/set` API; add typed helpers only if needed.  
    Reasoning: keeps `ContextStore` simple while avoiding “magic strings” spread everywhere.
3. **Error mapping and observability.**
  - In `app/utils/errors.py`, add the new exception types.  
    - In `app/api/main.py`, map them to HTTP codes and simple error payloads.  
    - Ensure logs contain correlation ids, session ids, and intent, but not sensitive data (e.g. raw student code by default).  
    Reasoning: good error surfaces and logs prevent production debugging pain.

---

### 5. Final Validation Before Release

1. **Run full test suite and fix regressions.**
  - All unit tests (new + existing).  
    - All integration tests, especially assessment and new routers.
2. ***Manual smoke tests.***
  - *Programming test: start → submit correct and incorrect solutions; check scores and performance summary.*  
    - *Visualization: a few chat prompts for diagrams/graphs; verify frontend rendering.*  
    - *Problem-solving: upload a sample problem, step through guardrail stages, confirm solution withholding when appropriate.*

  **How to run:**
  1. Start the API: `uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000` (or `./app/scripts/run_api.sh`). Ensure Docker is running for programming tests.
  2. **Programming test:**  
     - Start: `POST /api/v1/assessment/programming-test/start` with body `{"session_id": "smoke-s1", "user_id": "smoke-u1"}`.  
     - Submit a **correct** solution: `POST /api/v1/assessment/programming-test/submit` with `{"session_id": "smoke-s1", "user_id": "smoke-u1", "code": "<code that passes tests>"}`.  
     - Start a new test (new session_id), then submit an **incorrect** solution; confirm feedback/scores.  
     - Performance summary: `GET /api/v1/assessment/performance/smoke-u1`.
  3. **Visualization:**  
     - `POST /api/v1/visualization/generate` with body `{"description": "water cycle with evaporation and rain", "output_type": "diagram"}` and optionally `{"description": "bar chart of sales by quarter", "output_type": "graph"}`.  
     - Check response for `content` and `metadata` (e.g. `mermaid`, `chart_spec`); if you have a frontend, verify it renders the diagram/graph.
  4. **Problem-solving:**  
     - Start: `POST /api/v1/problem-solving/start` with multipart form `session_id`, `image` (file), optional `user_id`/`message`; or JSON with `session_id`, `image_base64`, optional `user_id`/`message`.  
     - Step through guardrails: `POST /api/v1/problem-solving/respond` with `{"session_id": "<same>", "answer": "<your text reply>"}`.  
     - Confirm that when fundamentals are weak, the assistant withholds the full solution and offers hints/similar problems instead.

  Interactive API docs: `http://localhost:8000/docs`.

3. **Review non-functional requirements.**
  - Confirm Docker resource limits and timeouts behave as expected.  
    - Verify large images and long code snippets do not break API limits.  
    - Check that logs and errors are safe and actionable.

Reasoning: a final structured pass reduces the risk of late surprises in production.