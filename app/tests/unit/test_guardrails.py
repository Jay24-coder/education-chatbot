"""
Unit tests for guardrail state machine.

Covers: no state → PROBE/ASSESS; weak understanding → EXPLAIN_CONCEPT/SIMILAR_PROBLEM;
strong understanding → progresses to SOLVE. Ensures educational behavior regardless of LLM variance.
"""

import pytest

from app.agents.problem_solving.guardrails import (
    Action,
    Analysis,
    GuardrailState,
    Stage,
    initial_state,
    next_state,
)


def test_starting_from_no_state_expects_probe_or_assess():
    """Starting from no state, next_state returns action PROBE or ASSESS."""
    analysis = Analysis(understanding="strong")  # analysis ignored when state is None

    state, action = next_state(None, "any input", analysis)

    assert action in (Action.PROBE, Action.ASSESS)
    assert state.stage in (Stage.PROBE, Stage.ASSESS)
    assert state.attempts == 0


def test_weak_understanding_stays_in_explain_concept_or_similar_problem():
    """Weak understanding keeps flow in EXPLAIN_CONCEPT or SIMILAR_PROBLEM."""
    current = initial_state()
    # After one probe, we're effectively in ASSESS; treat as having probe state with 1 attempt
    current = GuardrailState(
        stage=Stage.ASSESS,
        attempts=1,
        confidence_flags=frozenset(),
        topic=None,
        difficulty=None,
    )
    analysis_weak = Analysis(understanding="weak")

    state, action = next_state(current, "student response", analysis_weak)

    assert state.stage in (Stage.EXPLAIN_CONCEPT, Stage.SIMILAR_PROBLEM)
    assert action in (Action.EXPLAIN_CONCEPT, Action.GIVE_SIMILAR_PROBLEM)


def test_weak_understanding_from_explain_concept_gives_similar_problem():
    """When in EXPLAIN_CONCEPT and understanding is weak, can move to SIMILAR_PROBLEM."""
    current = GuardrailState(
        stage=Stage.EXPLAIN_CONCEPT,
        attempts=1,
        confidence_flags=frozenset(),
        topic=None,
        difficulty=None,
    )
    analysis_weak = Analysis(understanding="weak")

    state, action = next_state(current, "still confused", analysis_weak)

    assert state.stage == Stage.SIMILAR_PROBLEM
    assert action == Action.GIVE_SIMILAR_PROBLEM


def test_weak_understanding_from_similar_problem_re_explains():
    """When in SIMILAR_PROBLEM and understanding still weak, re-explain concept."""
    current = GuardrailState(
        stage=Stage.SIMILAR_PROBLEM,
        attempts=2,
        confidence_flags=frozenset(),
        topic=None,
        difficulty=None,
    )
    analysis_weak = Analysis(understanding="weak")

    state, action = next_state(current, "still wrong", analysis_weak)

    assert state.stage == Stage.EXPLAIN_CONCEPT
    assert action == Action.EXPLAIN_CONCEPT


def test_strong_understanding_progresses_to_solve():
    """Strong understanding from probe/assess progresses to SOLVE."""
    current = GuardrailState(
        stage=Stage.ASSESS,
        attempts=1,
        confidence_flags=frozenset(),
        topic=None,
        difficulty=None,
    )
    analysis_strong = Analysis(understanding="strong")

    state, action = next_state(current, "correct explanation", analysis_strong)

    assert state.stage == Stage.SOLVE
    assert action == Action.ALLOW_SOLVE
    assert "understanding_strong" in state.confidence_flags


def test_strong_understanding_from_explain_concept_progresses_to_solve():
    """Strong understanding from EXPLAIN_CONCEPT progresses to SOLVE."""
    current = GuardrailState(
        stage=Stage.EXPLAIN_CONCEPT,
        attempts=1,
        confidence_flags=frozenset(),
        topic="algebra",
        difficulty="medium",
    )
    analysis_strong = Analysis(understanding="strong")

    state, action = next_state(current, "I get it now", analysis_strong)

    assert state.stage == Stage.SOLVE
    assert action == Action.ALLOW_SOLVE
    assert state.topic == "algebra"
    assert state.difficulty == "medium"


def test_strong_understanding_from_similar_problem_progresses_to_solve():
    """Strong understanding from SIMILAR_PROBLEM progresses to SOLVE."""
    current = GuardrailState(
        stage=Stage.SIMILAR_PROBLEM,
        attempts=2,
        confidence_flags=frozenset(),
        topic=None,
        difficulty=None,
    )
    analysis_strong = Analysis(understanding="strong")

    state, action = next_state(current, "solved it", analysis_strong)

    assert state.stage == Stage.SOLVE
    assert action == Action.ALLOW_SOLVE


def test_partial_understanding_stays_in_explain_or_similar():
    """Partial understanding does not advance to SOLVE; stays in explain/similar flow."""
    current = GuardrailState(
        stage=Stage.ASSESS,
        attempts=1,
        confidence_flags=frozenset(),
        topic=None,
        difficulty=None,
    )
    analysis_partial = Analysis(understanding="partial")

    state, action = next_state(current, "partially correct", analysis_partial)

    assert state.stage in (Stage.EXPLAIN_CONCEPT, Stage.SIMILAR_PROBLEM)
    assert action in (Action.EXPLAIN_CONCEPT, Action.GIVE_SIMILAR_PROBLEM)
    assert state.stage != Stage.SOLVE


def test_already_in_solve_remains_allow_solve():
    """Once in SOLVE, state and action remain ALLOW_SOLVE."""
    current = GuardrailState(
        stage=Stage.SOLVE,
        attempts=2,
        confidence_flags=frozenset({"understanding_strong"}),
        topic=None,
        difficulty=None,
    )
    analysis = Analysis(understanding="strong")

    state, action = next_state(current, "working on problem", analysis)

    assert state.stage == Stage.SOLVE
    assert action == Action.ALLOW_SOLVE


def test_initial_state_has_probe_stage_zero_attempts():
    """initial_state() returns PROBE stage with 0 attempts."""
    state = initial_state()

    assert state.stage == Stage.PROBE
    assert state.attempts == 0
    assert state.confidence_flags == frozenset()


def test_initial_state_accepts_topic_and_difficulty():
    """initial_state(topic, difficulty) stores them in state."""
    state = initial_state(topic="quadratics", difficulty="hard")

    assert state.topic == "quadratics"
    assert state.difficulty == "hard"


def test_next_state_is_pure_same_input_same_output():
    """next_state is deterministic: same inputs give same outputs (pure function)."""
    current = GuardrailState(
        stage=Stage.ASSESS,
        attempts=1,
        confidence_flags=frozenset(),
        topic=None,
        difficulty=None,
    )
    analysis = Analysis(understanding="strong")

    state1, action1 = next_state(current, "yes", analysis)
    state2, action2 = next_state(current, "yes", analysis)

    assert state1.stage == state2.stage
    assert state1.attempts == state2.attempts
    assert action1 == action2
