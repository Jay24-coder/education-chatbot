"""
Guardrail logic for the problem-solving agent as pure, side-effect-free functions.

State model (stage, attempts, confidence flags, topic, difficulty) and
next_state(current_state, student_input, analysis) -> (new_state, action).
Analysis is a small struct summarizing LLM judgments (e.g. understanding: weak/partial/strong).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Stage(Enum):
    """Current stage of the problem-solving flow."""

    PROBE = "probe"  # Initial: probe what the student knows
    ASSESS = "assess"  # Assess understanding from response
    EXPLAIN_CONCEPT = "explain_concept"  # Explain the concept
    SIMILAR_PROBLEM = "similar_problem"  # Give a similar practice problem
    SOLVE = "solve"  # Student may work on the main problem


class Action(Enum):
    """Recommended action for the agent given current state and analysis."""

    PROBE = "probe"
    ASSESS = "assess"
    EXPLAIN_CONCEPT = "explain_concept"
    GIVE_SIMILAR_PROBLEM = "give_similar_problem"
    ALLOW_SOLVE = "allow_solve"


UnderstandingLevel = Literal["weak", "partial", "strong"]


@dataclass(frozen=True)
class Analysis:
    """Summary of LLM judgments about the student's response."""

    understanding: UnderstandingLevel


@dataclass(frozen=True)
class GuardrailState:
    """Immutable state for the guardrail state machine."""

    stage: Stage
    attempts: int = 0
    confidence_flags: frozenset[str] = field(default_factory=frozenset)
    topic: str | None = None
    difficulty: str | None = None


def next_state(
    current_state: GuardrailState | None,
    student_input: str,
    analysis: Analysis,
) -> tuple[GuardrailState, Action]:
    """
    Pure transition: (current_state, student_input, analysis) -> (new_state, action).

    No side effects. Given current state and LLM analysis of the student's input,
    returns the next state and the action the agent should take.
    """
    if current_state is None:
        # No state yet: first step is to PROBE or ASSESS
        return (initial_state(), Action.PROBE)

    if current_state.stage in (Stage.PROBE, Stage.ASSESS):
        # Have state from probe/assess; transition based on analysis
        return _transition_from_probe_or_assess(current_state, student_input, analysis)

    if current_state.stage in (Stage.EXPLAIN_CONCEPT, Stage.SIMILAR_PROBLEM):
        return _transition_from_explain_or_similar(current_state, student_input, analysis)

    # Already in SOLVE: maintain state, action is ALLOW_SOLVE
    return (current_state, Action.ALLOW_SOLVE)


def _transition_from_probe_or_assess(
    current: GuardrailState | None,
    student_input: str,
    analysis: Analysis,
) -> tuple[GuardrailState, Action]:
    """From PROBE/ASSESS: weak/partial -> explain or similar; strong -> SOLVE."""
    attempts = (current.attempts + 1) if current else 1
    topic = current.topic if current else None
    difficulty = current.difficulty if current else None
    flags = current.confidence_flags if current else frozenset()

    if analysis.understanding == "strong":
        new_state = GuardrailState(
            stage=Stage.SOLVE,
            attempts=attempts,
            confidence_flags=flags | {"understanding_strong"},
            topic=topic,
            difficulty=difficulty,
        )
        return (new_state, Action.ALLOW_SOLVE)

    if analysis.understanding == "weak":
        # Prefer explain concept first; after attempts could offer similar problem
        new_stage = Stage.EXPLAIN_CONCEPT if attempts <= 1 else Stage.SIMILAR_PROBLEM
        action = Action.EXPLAIN_CONCEPT if attempts <= 1 else Action.GIVE_SIMILAR_PROBLEM
        new_state = GuardrailState(
            stage=new_stage,
            attempts=attempts,
            confidence_flags=flags,
            topic=topic,
            difficulty=difficulty,
        )
        return (new_state, action)

    # partial: stay in explain/similar flow, do not advance to SOLVE
    new_stage = Stage.SIMILAR_PROBLEM if attempts >= 2 else Stage.EXPLAIN_CONCEPT
    action = Action.GIVE_SIMILAR_PROBLEM if attempts >= 2 else Action.EXPLAIN_CONCEPT
    new_state = GuardrailState(
        stage=new_stage,
        attempts=attempts,
        confidence_flags=flags,
        topic=topic,
        difficulty=difficulty,
    )
    return (new_state, action)


def _transition_from_explain_or_similar(
    current: GuardrailState,
    student_input: str,
    analysis: Analysis,
) -> tuple[GuardrailState, Action]:
    """From EXPLAIN_CONCEPT or SIMILAR_PROBLEM: weak/partial -> stay; strong -> SOLVE."""
    attempts = current.attempts + 1
    flags = current.confidence_flags
    topic = current.topic
    difficulty = current.difficulty

    if analysis.understanding == "strong":
        new_state = GuardrailState(
            stage=Stage.SOLVE,
            attempts=attempts,
            confidence_flags=flags | {"understanding_strong"},
            topic=topic,
            difficulty=difficulty,
        )
        return (new_state, Action.ALLOW_SOLVE)

    if analysis.understanding == "weak":
        # Stay in explain or move to similar
        if current.stage == Stage.EXPLAIN_CONCEPT:
            new_state = GuardrailState(
                stage=Stage.SIMILAR_PROBLEM,
                attempts=attempts,
                confidence_flags=flags,
                topic=topic,
                difficulty=difficulty,
            )
            return (new_state, Action.GIVE_SIMILAR_PROBLEM)
        # Already similar problem: stay and give another similar or re-explain
        new_state = GuardrailState(
            stage=Stage.EXPLAIN_CONCEPT,
            attempts=attempts,
            confidence_flags=flags,
            topic=topic,
            difficulty=difficulty,
        )
        return (new_state, Action.EXPLAIN_CONCEPT)

    # partial: alternate or stay
    if current.stage == Stage.EXPLAIN_CONCEPT:
        new_state = GuardrailState(
            stage=Stage.SIMILAR_PROBLEM,
            attempts=attempts,
            confidence_flags=flags,
            topic=topic,
            difficulty=difficulty,
        )
        return (new_state, Action.GIVE_SIMILAR_PROBLEM)
    new_state = GuardrailState(
        stage=Stage.EXPLAIN_CONCEPT,
        attempts=attempts,
        confidence_flags=flags,
        topic=topic,
        difficulty=difficulty,
    )
    return (new_state, Action.EXPLAIN_CONCEPT)


def initial_state(topic: str | None = None, difficulty: str | None = None) -> GuardrailState:
    """Return the initial state (PROBE) before any student input."""
    return GuardrailState(
        stage=Stage.PROBE,
        attempts=0,
        confidence_flags=frozenset(),
        topic=topic,
        difficulty=difficulty,
    )


def state_to_dict(state: GuardrailState) -> dict:
    """Serialize GuardrailState for storage in ContextStore."""
    return {
        "stage": state.stage.value,
        "attempts": state.attempts,
        "confidence_flags": list(state.confidence_flags),
        "topic": state.topic,
        "difficulty": state.difficulty,
    }


def state_from_dict(data: dict) -> GuardrailState | None:
    """Deserialize GuardrailState from ContextStore. Returns None if data is invalid."""
    if not data or not isinstance(data, dict):
        return None
    try:
        stage_val = data.get("stage", "probe")
        stage = Stage(stage_val) if isinstance(stage_val, str) else Stage.PROBE
    except ValueError:
        stage = Stage.PROBE
    attempts = int(data["attempts"]) if isinstance(data.get("attempts"), (int, float)) else 0
    flags = data.get("confidence_flags")
    if isinstance(flags, list):
        flags = frozenset(str(f) for f in flags)
    else:
        flags = frozenset()
    topic = data.get("topic") if isinstance(data.get("topic"), str) else None
    difficulty = data.get("difficulty") if isinstance(data.get("difficulty"), str) else None
    return GuardrailState(
        stage=stage,
        attempts=attempts,
        confidence_flags=flags,
        topic=topic,
        difficulty=difficulty,
    )
