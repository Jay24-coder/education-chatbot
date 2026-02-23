"""Unit tests for question bank: retrieval by topic+difficulty, LLM fallback."""

import pytest

from app.agents.shared_tools.question_bank import (
    DifficultyLevel,
    TopicArea,
    Question,
    QuestionBank,
    _parse_llm_question,
)


class TestQuestionBankRetrieval:
    """Test retrieval by topic and difficulty for seeded questions."""

    @pytest.mark.asyncio
    async def test_returns_question_for_seeded_topic_and_difficulty(self):
        bank = QuestionBank()
        q = await bank.get_question(TopicArea.ALGEBRA, DifficultyLevel.BEGINNER)
        assert isinstance(q, Question)
        assert q.topic == "algebra"
        assert q.difficulty == "beginner"
        assert q.text
        assert q.correct_answer
        assert q.source == "seed"

    @pytest.mark.asyncio
    async def test_returns_question_for_string_topic_and_difficulty(self):
        bank = QuestionBank()
        q = await bank.get_question("calculus", "intermediate")
        assert q.topic == "calculus"
        assert q.difficulty == "intermediate"
        assert q.source == "seed"

    @pytest.mark.asyncio
    async def test_returns_question_for_all_seeded_areas(self):
        bank = QuestionBank()
        for topic in [TopicArea.ALGEBRA, TopicArea.CALCULUS, TopicArea.KINEMATICS, TopicArea.WAVES]:
            q = await bank.get_question(topic, DifficultyLevel.ADVANCED)
            assert q.topic == topic.value
            assert q.difficulty == "advanced"
            assert q.text and q.correct_answer

    @pytest.mark.asyncio
    async def test_different_difficulties_return_valid_questions(self):
        bank = QuestionBank()
        for diff in DifficultyLevel:
            q = await bank.get_question("algebra", diff)
            assert q.difficulty == diff.value
            assert q.text


class TestQuestionBankLLMFallback:
    """Test LLM fallback when no seed for topic/difficulty."""

    @pytest.mark.asyncio
    async def test_fallback_placeholder_when_no_llm(self):
        bank = QuestionBank()
        q = await bank.get_question("nonexistent_topic", "beginner", llm_provider=None)
        assert q.source == "fallback"
        assert "No seed question" in q.text or "nonexistent_topic" in q.text

    @pytest.mark.asyncio
    async def test_llm_fallback_returns_llm_question_when_mock_returns_structured(self):
        class MockLLM:
            async def complete(self, prompt, *, model=None, temperature=0.3, timeout_seconds=None):
                return (
                    "What is 2 + 2?\n"
                    "CORRECT: 4\n"
                    "A. 3\n"
                    "B. 4\n"
                    "C. 5\n"
                    "D. 6\n"
                )
        bank = QuestionBank()
        # Use a topic/difficulty that might have no seed, or build a bank with empty seed
        bank._questions = []
        q = await bank.get_question("algebra", "beginner", llm_provider=MockLLM())
        assert q.source == "llm"
        assert "2 + 2" in q.text or q.text
        assert q.correct_answer == "4"
        assert len(q.options) >= 1

    @pytest.mark.asyncio
    async def test_llm_fallback_on_exception_returns_safe_question(self):
        class FailingLLM:
            async def complete(self, prompt, *, model=None, temperature=0.3, timeout_seconds=None):
                raise RuntimeError("API error")
        bank = QuestionBank()
        bank._questions = []
        q = await bank.get_question("algebra", "beginner", llm_provider=FailingLLM())
        assert q.source == "llm"
        assert "LLM failed" in q.text or "question" in q.text.lower()


class TestParseLlmQuestion:
    """Test parsing of LLM-generated question text."""

    def test_parses_correct_and_options(self):
        text = "What is 2+2?\nCORRECT: 4\nA. 3\nB. 4\nC. 5"
        q_text, correct, opts = _parse_llm_question(text)
        assert "2+2" in q_text
        assert correct == "4"
        assert "4" in opts
        assert len(opts) >= 2

    def test_handles_empty_response(self):
        q_text, correct, opts = _parse_llm_question("")
        assert q_text == ""
        assert correct == ""
        assert opts == []
