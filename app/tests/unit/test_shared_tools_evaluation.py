"""Unit tests for evaluation (scoring) utilities."""

import pytest

from app.agents.shared_tools.evaluation import (
    score_mcq,
    score_freetext,
    build_feedback,
)


class TestScoreMcq:
    """Test MCQ scoring: exact match, partial credit, zero."""

    def test_exact_match_returns_one(self):
        assert score_mcq("5", "5") == 1.0
        assert score_mcq(" 5 ", "5") == 1.0
        assert score_mcq("ALGEBRA", "algebra") == 1.0

    def test_wrong_answer_returns_zero(self):
        assert score_mcq("3", "5") == 0.0
        assert score_mcq("", "5") == 0.0
        assert score_mcq("wrong", "right") == 0.0

    def test_partial_credit_returns_half(self):
        assert score_mcq("almost", "exact", partial_credit_answers=["almost"]) == 0.5
        assert score_mcq("  B  ", "A", partial_credit_answers=["B", "C"]) == 0.5

    def test_partial_credit_ignored_when_exact_match(self):
        assert score_mcq("correct", "correct", partial_credit_answers=["correct"]) == 1.0

    def test_partial_credit_none_returns_zero(self):
        assert score_mcq("other", "exact", partial_credit_answers=None) == 0.0


class TestScoreFreetext:
    """Test free-text scoring with mock LLM."""

    @pytest.mark.asyncio
    async def test_parses_number_from_llm_response(self):
        class MockLLM:
            async def complete(self, prompt, *, model=None, temperature=0.0, timeout_seconds=None):
                return "0.8"
        score = await score_freetext("my answer", "check understanding", MockLLM())
        assert score == 0.8

    @pytest.mark.asyncio
    async def test_clamps_score_to_unit_interval(self):
        class MockLLM:
            async def complete(self, prompt, *, model=None, temperature=0.0, timeout_seconds=None):
                return "1.5"
        score = await score_freetext("x", "y", MockLLM())
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_number_in_response(self):
        class MockLLM:
            async def complete(self, prompt, *, model=None, temperature=0.0, timeout_seconds=None):
                return "The answer is good."
        score = await score_freetext("x", "y", MockLLM())
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_returns_zero_on_negative_parsed(self):
        class MockLLM:
            async def complete(self, prompt, *, model=None, temperature=0.0, timeout_seconds=None):
                return "-0.2"
        score = await score_freetext("x", "y", MockLLM())
        assert score == 0.0


class TestBuildFeedback:
    """Test feedback string builder."""

    def test_correct_with_answer(self):
        out = build_feedback(1.0, "42")
        assert "Correct" in out and "42" in out

    def test_correct_without_answer(self):
        out = build_feedback(1.0, None)
        assert out == "Correct!"

    def test_partial_with_answer(self):
        out = build_feedback(0.5, "full answer")
        assert "Partially" in out and "full answer" in out

    def test_wrong_with_answer(self):
        out = build_feedback(0.0, "correct one")
        assert "Not quite" in out and "correct one" in out

    def test_wrong_without_answer(self):
        out = build_feedback(0.0, None)
        assert out == "Not quite."
