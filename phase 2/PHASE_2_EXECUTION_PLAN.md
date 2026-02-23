**PHASE 2 EXECUTION PLAN**

**Assessment System**

*Educational Chatbot --- Multi-Agent Architecture*

**Weeks 3--4**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p><strong>What Phase 2 Delivers</strong></p>
<p>Quiz Agent • Concept Test Agent • Performance Monitor Agent</p>
<p>Scoring Utilities • Extended ContextStore • Assessment API Endpoints</p></td>
</tr>
</tbody>
</table>

*Builds on Phase 1: Orchestrator, Information Agents, ContextStore, LLMProvider*

# **1. Overview & Goals** {#overview-goals}

Phase 2 extends the foundation built in Phase 1 by introducing the Assessment System --- the engine that evaluates student understanding and tracks performance over time. Three new agents are the core deliverables: the Quiz Agent, the Concept Test Agent, and the Performance Monitor Agent.

By the end of Phase 2 the system will be able to:

- Generate adaptive quizzes for math and physics topics at the appropriate difficulty level

<!-- -->

- Conduct multi-turn conversational concept checks that probe for genuine understanding

- Persist performance metrics per student across sessions

- Route assessment requests through the existing Orchestrator with zero changes to the API contract

- Lay the data foundation for the faculty alert system arriving in Phase 4

|                                                                                             |
|---------------------------------------------------------------------------------------------|
| **Phase 2 Scope (Fixed)**                                                                   |
| IN SCOPE: Quiz Agent, Concept Test Agent, Performance Monitor Agent, scoring utilities,     |
| assessment API endpoints, extended ContextStore schema, updated Orchestrator routing.       |
| DEFERRED: Interview Agent (Phase 3), Programming Test Agent (Phase 3), faculty notification |
| (Phase 4), Problem-Solving / Visualization agents (Phase 3), Redis / Postgres (Phase 3+).   |

# **2. Features Delivered** {#features-delivered}

| **Feature**                   | **Primary Agent**         | **Supporting Agents**              | **Key Output**                         |
|-------------------------------|---------------------------|------------------------------------|----------------------------------------|
| **5. Short Quiz**             | Quiz Agent                | Performance Monitor                | Scored quiz with per-question feedback |
| **7. Concept Test (Verbal)**  | Concept Test Agent        | Performance Monitor                | Multi-turn mastery score               |
| **9. Performance Foundation** | Performance Monitor Agent | ContextStore, future Faculty Alert | Per-student metrics store              |

Features 6 (Programming Test) and 8 (Viva/Interview) are Assessment agents but are deferred to Phase 3 where the Problem-Solving scaffolding and the LLM evaluation rubrics will be more mature.

# **3. Architecture Delta from Phase 1** {#architecture-delta-from-phase-1}

The table below shows every new file and every Phase 1 file that must be modified.

| **Action** | **File / Module**                                  | **Reason**                                 |
|------------|----------------------------------------------------|--------------------------------------------|
| **NEW**    | app/agents/assessment/quiz_agent.py                | Quiz Agent implementation                  |
| **NEW**    | app/agents/assessment/concept_test_agent.py        | Concept Test Agent                         |
| **NEW**    | app/agents/monitoring/performance_monitor_agent.py | Performance Monitor Agent                  |
| **NEW**    | app/agents/shared_tools/evaluation.py              | Scoring & rubric utilities                 |
| **NEW**    | app/agents/shared_tools/question_bank.py           | In-memory question bank with LLM fallback  |
| **NEW**    | app/api/routers/assessment.py                      | Quiz and concept-test API endpoints        |
| **NEW**    | app/api/schemas/v1/assessment.py                   | Pydantic models for assessment API         |
| **MODIFY** | app/orchestrator/wiring.py                         | Register new agents in registry            |
| **MODIFY** | app/orchestrator/routing.py                        | Add QUIZ, CONCEPT_TEST, ASSESSMENT intents |
| **MODIFY** | app/orchestrator/types.py                          | Extend Intent enum                         |
| **MODIFY** | app/services/context/store.py                      | Add performance-metrics methods            |
| **MODIFY** | app/services/context/memory_store.py               | Implement new metrics methods              |
| **MODIFY** | app/api/main.py                                    | Include assessment router                  |
| **MODIFY** | app/tests/ (multiple)                              | New unit + integration tests               |

# **4. Key Design Decisions** {#key-design-decisions}

## **4.1 Question Bank Strategy** {#question-bank-strategy}

Use a hybrid approach: a seeded in-memory question bank for core math and physics topics, with LLM-generated fallback when a topic or difficulty level is not covered. This balances consistency (important for repeatable assessments) with flexibility.

- Seed with \~20--30 questions per major topic at three difficulty levels: beginner, intermediate, advanced

- LLMProvider generates questions on-the-fly for gaps; mark generated questions with a source flag

- Store in app/agents/shared_tools/question_bank.py as a typed dataclass structure

## **4.2 Stateless Agents, State in ContextStore** {#stateless-agents-state-in-contextstore}

Agents remain stateless (per the Phase 1 principle). Quiz and Concept Test agents emit result events; the Performance Monitor Agent writes them to the ContextStore. No agent holds mutable state in memory between requests.

## **4.3 Multi-Turn Concept Test** {#multi-turn-concept-test}

The Concept Test Agent is inherently conversational. It must recover the in-progress test state from ContextStore on each turn. The session key schema below governs this:

|                                                                                   |
|-----------------------------------------------------------------------------------|
| **ContextStore Key Schema (Assessment)**                                          |
| concept_test:{session_id}:state → { topic, turn, questions_asked, score, status } |
| quiz:{session_id}:state → { quiz_id, questions, answers, current_q, score }       |
| perf:{user_id}:metrics → { quizzes: \[\], concept_tests: \[\], last_activity }    |
| perf:{user_id}:summary → { avg_score, weak_topics, strong_topics, alert_flag }    |

## **4.4 Performance Monitor as a Service, Not Just an Agent** {#performance-monitor-as-a-service-not-just-an-agent}

The Performance Monitor Agent handles routing from the Orchestrator for explicit performance queries (e.g., \'How am I doing?\'). But it also exposes a direct service interface so other agents (Quiz, Concept Test) can log results without going through the Orchestrator. This avoids circular routing.

- app/agents/monitoring/performance_monitor_agent.py implements both the BaseAgent protocol and a PerformanceService protocol

- Dependency-injected via app/api/deps.py alongside the orchestrator

# **5. Execution Plan** {#execution-plan}

Tasks follow the same dependency-first ordering as Phase 1. Each step closes with a checkpoint before proceeding.

## **Step 1: Extend ContextStore for Metrics (Week 3, Days 1--2)**

All assessment agents depend on performance persistence. Do this first.

| **\#**  | **Task**                                     | **Details / Notes**                                                                                  | **Location**                            |
|---------|----------------------------------------------|------------------------------------------------------------------------------------------------------|-----------------------------------------|
| **1.1** | Add metrics methods to ContextStore protocol | append_assessment_result(user_id, result), get_performance_summary(user_id), update_summary(user_id) | app/services/context/store.py           |
| **1.2** | Implement new methods in MemoryStore         | In-memory dict: perf_data\[user_id\] = {quizzes:\[\], concept_tests:\[\]}                            | app/services/context/memory_store.py    |
| **1.3** | Extend AgentResponse / metadata types        | Add result_type, score, topic fields to metadata dict in AgentResponse                               | app/orchestrator/types.py               |
| **1.4** | Extend Intent enum                           | Add QUIZ, CONCEPT_TEST, ASSESSMENT, PERFORMANCE intents                                              | app/orchestrator/types.py               |
| **1.5** | Write unit tests for new store methods       | append, get_summary, update; assert correct accumulation                                             | app/tests/unit/test_services_context.py |

|       |                                                                                                                  |
|-------|------------------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** ContextStore stores and retrieves assessment results; Intent enum includes all four new intents. |

## **Step 2: Shared Evaluation & Question Bank Utilities (Week 3, Days 2--3)** {#step-2-shared-evaluation-question-bank-utilities-week-3-days-23}

Shared tools used by both Quiz and Concept Test agents. Build once, test once.

| **\#**  | **Task**                                    | **Details / Notes**                                                                                                                             | **Location**                                   |
|---------|---------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| **2.1** | Create evaluation.py with scoring utilities | score_mcq(answer, correct) → float; score_freetext(answer, rubric, llm_provider) → float; build_feedback(score, correct_answer) → str           | app/agents/shared_tools/evaluation.py          |
| **2.2** | Create question_bank.py with seed data      | QuestionBank dataclass; seed \~20 questions per topic (algebra, calculus, kinematics, waves); get_question(topic, difficulty) with LLM fallback | app/agents/shared_tools/question_bank.py       |
| **2.3** | Define difficulty enum and topic taxonomy   | DifficultyLevel.BEGINNER/INTERMEDIATE/ADVANCED; TopicArea enum aligned with syllabus KB                                                         | app/agents/shared_tools/question_bank.py       |
| **2.4** | Unit test scoring utilities                 | Test MCQ exact match, partial credit, zero; test freetext with mock LLM                                                                         | app/tests/unit/test_shared_tools_evaluation.py |
| **2.5** | Unit test question bank                     | Test retrieval by topic+difficulty; test LLM fallback path with mock provider                                                                   | app/tests/unit/test_shared_tools_qbank.py      |

|       |                                                                                                                                                               |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** evaluation.py scores both MCQ and free-text answers; question_bank.py returns questions for all seeded topics with correct fallback behavior. |

## **Step 3: Performance Monitor Agent (Week 3, Days 3--4)**

Build this before Quiz/Concept Test agents because they both depend on it for result logging.

| **\#**  | **Task**                                    | **Details / Notes**                                                                                                                                   | **Location**                                        |
|---------|---------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| **3.1** | Implement PerformanceMonitorAgent           | process_request() handles PERFORMANCE intent (e.g., \'show my progress\'); agent_id = performance_monitor; capabilities = \[PERFORMANCE, ASSESSMENT\] | app/agents/monitoring/performance_monitor_agent.py  |
| **3.2** | Implement log_result() service method       | log_result(user_id, result: AssessmentResult) → writes to ContextStore; used by other agents directly                                                 | app/agents/monitoring/performance_monitor_agent.py  |
| **3.3** | Implement get_summary() and format response | Reads perf metrics from ContextStore; formats as human-readable summary; flags weak topics                                                            | app/agents/monitoring/performance_monitor_agent.py  |
| **3.4** | Define AssessmentResult type                | AssessmentResult: user_id, session_id, type (quiz/concept), topic, score, timestamp, metadata                                                         | app/orchestrator/types.py or app/agents/monitoring/ |
| **3.5** | Register agent and update wiring/routing    | Add to build_agent_registry(); map PERFORMANCE and ASSESSMENT intents                                                                                 | app/orchestrator/wiring.py, routing.py              |
| **3.6** | Unit tests for Performance Monitor          | Test log_result accumulation; test summary formatting; test weak-topic detection                                                                      | app/tests/unit/test_agents_performance_monitor.py   |

|       |                                                                                                                                                      |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** Performance Monitor logs results, reads summaries, identifies weak topics, and is reachable via Orchestrator for PERFORMANCE intent. |

## **Step 4: Quiz Agent (Week 3, Days 5--7)**

| **\#**  | **Task**                              | **Details / Notes**                                                                                                                                    | **Location**                        |
|---------|---------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| **4.1** | Implement QuizAgent skeleton          | agent_id = quiz; capabilities = \[QUIZ\]; process_request() dispatches to start_quiz() or submit_answer() based on session state                       | app/agents/assessment/quiz_agent.py |
| **4.2** | Implement start_quiz()                | Reads topic + difficulty from request; fetches N questions from QuestionBank; stores quiz state in ContextStore under quiz:{session_id}:state          | app/agents/assessment/quiz_agent.py |
| **4.3** | Implement submit_answer() and scoring | Retrieve current question from state; call evaluation.score_mcq or score_freetext; update state; return feedback; advance to next question or finalize | app/agents/assessment/quiz_agent.py |
| **4.4** | Implement finalize_quiz()             | Calculate total score; call performance_monitor.log_result(); return final summary with per-question breakdown                                         | app/agents/assessment/quiz_agent.py |
| **4.5** | Adaptive difficulty logic             | After each answer: if 2 consecutive correct → increment difficulty; if 2 consecutive wrong → decrement; update question selection accordingly          | app/agents/assessment/quiz_agent.py |
| **4.6** | Register and wire Quiz Agent          | Add to registry; map QUIZ intent; inject QuestionBank and PerformanceMonitor                                                                           | app/orchestrator/wiring.py          |
| **4.7** | Unit tests for Quiz Agent             | Test quiz start, answer submission, scoring, finalization; test adaptive difficulty trigger                                                            | app/tests/unit/test_agents_quiz.py  |

|       |                                                                                                                                 |
|-------|---------------------------------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** Full quiz flow works end-to-end: start → answer → feedback → finalize with score logged to Performance Monitor. |

## **Step 5: Concept Test Agent (Week 4, Days 1--3)**

The most complex Phase 2 agent due to multi-turn state management and free-text evaluation.

| **\#**  | **Task**                             | **Details / Notes**                                                                                                                                         | **Location**                                |
|---------|--------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| **5.1** | Implement ConceptTestAgent skeleton  | agent_id = concept_test; capabilities = \[CONCEPT_TEST\]; process_request() checks ContextStore to determine if session is new or continuing                | app/agents/assessment/concept_test_agent.py |
| **5.2** | Implement start_concept_test()       | Accept topic from request; generate 3--5 probing questions via LLMProvider with structured prompt; store state in concept_test:{session_id}:state           | app/agents/assessment/concept_test_agent.py |
| **5.3** | Implement evaluate_answer() per turn | Call evaluation.score_freetext() with rubric generated from question; store partial score; generate follow-up question if understanding is shallow          | app/agents/assessment/concept_test_agent.py |
| **5.4** | Implement finalize_concept_test()    | Aggregate turn scores; determine mastery level (FULL / PARTIAL / NEEDS_REVIEW); call performance_monitor.log_result(); return summary with explanation gaps | app/agents/assessment/concept_test_agent.py |
| **5.5** | Follow-up logic                      | If student answer scores below 0.6: LLM generates a simpler follow-up; max 2 follow-ups per question; prevents infinite loops                               | app/agents/assessment/concept_test_agent.py |
| **5.6** | Register and wire Concept Test Agent | Add to registry; map CONCEPT_TEST intent                                                                                                                    | app/orchestrator/wiring.py                  |
| **5.7** | Unit tests                           | Test new session, continuing session, low-score follow-up trigger, finalization                                                                             | app/tests/unit/test_agents_concept_test.py  |

|       |                                                                                                                                                            |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** Multi-turn concept test completes across multiple requests; state persists correctly between turns; results logged to Performance Monitor. |

## **Step 6: Assessment API Endpoints (Week 4, Days 3--4)**

| **\#**  | **Task**                           | **Details / Notes**                                                                                                                                                                                            | **Location**                     |
|---------|------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| **6.1** | Create assessment Pydantic schemas | QuizStartRequest, QuizAnswerRequest, QuizResponse; ConceptTestStartRequest, ConceptTestTurnRequest, ConceptTestResponse; PerformanceSummaryResponse                                                            | app/api/schemas/v1/assessment.py |
| **6.2** | Create assessment router           | POST /api/v1/assessment/quiz/start; POST /api/v1/assessment/quiz/answer; POST /api/v1/assessment/concept-test/start; POST /api/v1/assessment/concept-test/answer; GET /api/v1/assessment/performance/{user_id} | app/api/routers/assessment.py    |
| **6.3** | Wire router into FastAPI app       | Include assessment router in app/api/main.py with /api/v1 prefix                                                                                                                                               | app/api/main.py                  |
| **6.4** | Update deps.py                     | Inject QuestionBank, PerformanceMonitorAgent as dependencies available to assessment router                                                                                                                    | app/api/deps.py                  |
| **6.5** | Add error handling                 | Handle QuizNotFoundError, TestAlreadyCompleteError, InvalidSessionError with proper HTTP codes                                                                                                                 | app/api/routers/assessment.py    |

|       |                                                                                                                          |
|-------|--------------------------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** All assessment endpoints reachable via HTTP; correct status codes for error cases; OpenAPI docs updated. |

## **Step 7: Integration Tests & Quality (Week 4, Days 5--6)** {#step-7-integration-tests-quality-week-4-days-56}

| **\#**  | **Task**                                              | **Details / Notes**                                                                                                                         | **Location**                                  |
|---------|-------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| **7.1** | Integration test: full quiz flow via API              | POST /quiz/start → POST /quiz/answer (x N) → assert final score; assert ContextStore has result; assert Performance Monitor summary updated | app/tests/integration/test_assessment_flow.py |
| **7.2** | Integration test: multi-turn concept test via API     | POST /concept-test/start → POST /concept-test/answer (x turns) → assert mastery level returned; assert session continuity                   | app/tests/integration/test_assessment_flow.py |
| **7.3** | Integration test: performance summary endpoint        | Run quiz + concept test; GET /performance/{user_id}; assert both results present in summary                                                 | app/tests/integration/test_assessment_flow.py |
| **7.4** | Test routing: QUIZ and CONCEPT_TEST via chat endpoint | POST /api/v1/chat with quiz-intent message; assert Orchestrator routes to Quiz Agent                                                        | app/tests/integration/test_api_flow.py        |
| **7.5** | Test error/edge cases                                 | Submit answer to non-existent quiz; start concept test twice same session; assert correct errors returned                                   | app/tests/integration/test_assessment_flow.py |
| **7.6** | Test adaptive difficulty over simulated session       | Simulate 4 correct answers; assert difficulty escalates; simulate 4 wrong; assert difficulty drops                                          | app/tests/unit/test_agents_quiz.py            |

|       |                                                                                                       |
|-------|-------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** All integration tests pass; edge cases handled; Phase 1 regression tests still green. |

## **Step 8: Documentation & Deliverables (Week 4, Day 7)** {#step-8-documentation-deliverables-week-4-day-7}

| **\#**  | **Task**                                         | **Details / Notes**                                                                              | **Location**                  |
|---------|--------------------------------------------------|--------------------------------------------------------------------------------------------------|-------------------------------|
| **8.1** | Update README with Phase 2 endpoints             | Document /quiz/start, /quiz/answer, /concept-test/start, /concept-test/answer, /performance/{id} | README.md                     |
| **8.2** | Update IMPLEMENTATION_SUMMARY.md                 | Add entries for all new and modified files                                                       | IMPLEMENTATION_SUMMARY.md     |
| **8.3** | Add seed data script entries                     | Extend app/scripts/seed_data.py with question bank seeding                                       | app/scripts/seed_data.py      |
| **8.4** | Extend smoke test                                | Add quiz + concept-test flows to app/scripts/smoke_test.py                                       | app/scripts/smoke_test.py     |
| **8.5** | Optional: add assessment section to OpenAPI tags | Group quiz, concept-test, performance under \'Assessment\' tag in FastAPI router                 | app/api/routers/assessment.py |

|       |                                                                                                                        |
|-------|------------------------------------------------------------------------------------------------------------------------|
| **✓** | **Checkpoint:** New developer can run full assessment flow from README alone; smoke test covers all Phase 2 endpoints. |

# **6. Success Criteria** {#success-criteria}

|                                                                                                |
|------------------------------------------------------------------------------------------------|
| **Phase 2 is complete when all of the following are true**                                     |
| 1\. Quiz Agent generates and scores a complete adaptive quiz end-to-end.                       |
| 2\. Concept Test Agent completes a multi-turn verbal test with correct state across turns.     |
| 3\. Performance Monitor persists results and returns a human-readable summary.                 |
| 4\. Orchestrator routes QUIZ, CONCEPT_TEST, and PERFORMANCE intents to the correct agent.      |
| 5\. Assessment API endpoints respond with \< 2s for in-memory / mock-LLM runs.                 |
| 6\. All Phase 1 regression tests remain green.                                                 |
| 7\. Unit and integration tests cover the full assessment flow and all error paths.             |
| 8\. ContextStore correctly segregates quiz state, concept-test state, and performance metrics. |

# **7. Phase 2.5 Items to Weave In** {#phase-2.5-items-to-weave-in}

The following items should be added during Phase 2 where noted, even though they are not primary deliverables:

- Correlation / request IDs must propagate into all assessment agent logs (same pattern as Phase 1).

- All new agents must implement health_check(); register with the lifecycle manager.

- QuizAgent and ConceptTestAgent must be fully stateless; assert no instance-level mutable fields in code review.

- Strict Pydantic models for all assessment API I/O --- no raw dicts passed between layers.

- Performance Monitor alert_flag field should be set (but not yet acted upon) when avg_score \< 0.5 over last 5 assessments. Faculty notification wiring comes in Phase 4.

- Optional: stub a Redis-backed context store (app/services/context/redis_store.py) alongside the memory store so it can be activated by env var in Phase 3.

# **8. Phase 3 Preview** {#phase-3-preview}

Phase 3 (Weeks 5--6) builds the Specialized Agents. With the Assessment System and Performance Monitor in place, Phase 3 can focus on the most technically complex features:

| **Agent**                  | **Key Challenge**                                                  | **Phase 2 Dependency**                                                                |
|----------------------------|--------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| **Problem-Solving Agent**  | Image OCR + guardrails: probe understanding before giving solution | Uses Performance Monitor to check student level before deciding how much help to give |
| **Visualization Agent**    | Diagram / chart generation from concept descriptions               | Topic taxonomy from Question Bank guides what to visualize                            |
| **Programming Test Agent** | Code execution sandbox + multi-test-case evaluation                | Scoring utilities from evaluation.py can be extended for code                         |
| **Interview Agent (Viva)** | Session-long conversational assessment with holistic scoring       | Concept Test multi-turn pattern can be extended                                       |

# **9. File Map** {#file-map}

Complete reference of Phase 2 files and their locations under app/.

| **Phase 2 Concept**                  | **Location under app/**                            | **Status**       |
|--------------------------------------|----------------------------------------------------|------------------|
| Quiz Agent                           | app/agents/assessment/quiz_agent.py                | **NEW**          |
| Concept Test Agent                   | app/agents/assessment/concept_test_agent.py        | **NEW**          |
| Performance Monitor Agent            | app/agents/monitoring/performance_monitor_agent.py | **NEW**          |
| Scoring & evaluation utilities       | app/agents/shared_tools/evaluation.py              | **NEW**          |
| Question bank                        | app/agents/shared_tools/question_bank.py           | **NEW**          |
| Assessment API router                | app/api/routers/assessment.py                      | **NEW**          |
| Assessment Pydantic schemas          | app/api/schemas/v1/assessment.py                   | **NEW**          |
| Assessment result type               | app/orchestrator/types.py                          | **MODIFY**       |
| New intents (QUIZ, CONCEPT_TEST\...) | app/orchestrator/types.py                          | **MODIFY**       |
| Updated routing rules                | app/orchestrator/routing.py                        | **MODIFY**       |
| Updated agent wiring                 | app/orchestrator/wiring.py                         | **MODIFY**       |
| Extended ContextStore protocol       | app/services/context/store.py                      | **MODIFY**       |
| Extended MemoryStore                 | app/services/context/memory_store.py               | **MODIFY**       |
| App factory with assessment router   | app/api/main.py                                    | **MODIFY**       |
| DI for new agents                    | app/api/deps.py                                    | **MODIFY**       |
| Unit + integration tests             | app/tests/unit/ + integration/                     | **NEW / MODIFY** |

*End of Phase 2 Execution Plan*
