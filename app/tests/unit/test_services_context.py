"""Unit tests for ContextStore (MemoryStore) and ContextManager."""

import pytest

from app.orchestrator.context_manager import ContextManager
from app.services.context.memory_store import MemoryStore


class TestMemoryStore:
    """Tests for MemoryStore (in-memory ContextStore implementation)."""

    def test_get_missing_session_returns_empty_dict(self, memory_store: MemoryStore):
        assert memory_store.get("no-such-session") == {}
        assert memory_store.get("no-such-session", key="x") == {}

    def test_set_and_get(self, memory_store: MemoryStore):
        memory_store.set("s1", "key1", "value1")
        assert memory_store.get("s1") == {"key1": "value1"}
        assert memory_store.get("s1", key="key1") == {"key1": "value1"}

    def test_get_missing_key_returns_empty_dict(self, memory_store: MemoryStore):
        memory_store.set("s1", "a", 1)
        assert memory_store.get("s1", key="b") == {}

    def test_set_many(self, memory_store: MemoryStore):
        memory_store.set_many("s1", {"a": 1, "b": 2})
        assert memory_store.get("s1") == {"a": 1, "b": 2}

    def test_append_message_and_get_history(self, memory_store: MemoryStore):
        memory_store.append_message("s1", "user", "hello")
        memory_store.append_message("s1", "assistant", "hi there")
        history = memory_store.get_history("s1")
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "hello"}
        assert history[1] == {"role": "assistant", "content": "hi there"}

    def test_get_history_with_limit(self, memory_store: MemoryStore):
        memory_store.append_message("s1", "user", "1")
        memory_store.append_message("s1", "assistant", "2")
        memory_store.append_message("s1", "user", "3")
        assert len(memory_store.get_history("s1", limit=2)) == 2
        assert memory_store.get_history("s1", limit=2)[-1]["content"] == "3"

    def test_delete_key(self, memory_store: MemoryStore):
        memory_store.set_many("s1", {"a": 1, "b": 2})
        memory_store.delete("s1", key="a")
        assert memory_store.get("s1") == {"b": 2}

    def test_delete_session_removes_all(self, memory_store: MemoryStore):
        memory_store.set("s1", "x", 1)
        memory_store.append_message("s1", "user", "hi")
        memory_store.delete("s1", key=None)
        assert memory_store.get("s1") == {}
        assert memory_store.get_history("s1") == []

    # --- Performance / assessment metrics (Phase 2 Step 1) ---

    def test_append_assessment_result_quiz_accumulates(self, memory_store: MemoryStore):
        memory_store.append_assessment_result("u1", {"type": "quiz", "topic": "algebra", "score": 0.8})
        memory_store.append_assessment_result("u1", {"type": "quiz", "topic": "calculus", "score": 0.6})
        memory_store.update_summary("u1")
        summary = memory_store.get_performance_summary("u1")
        assert summary["avg_score"] == 0.7
        assert "algebra" in summary["strong_topics"]
        assert "calculus" not in summary["weak_topics"] and "calculus" not in summary["strong_topics"]

    def test_append_assessment_result_concept_test_accumulates(self, memory_store: MemoryStore):
        memory_store.append_assessment_result("u2", {"type": "concept_test", "topic": "waves", "score": 0.4})
        memory_store.append_assessment_result("u2", {"type": "concept_test", "topic": "kinematics", "score": 0.9})
        memory_store.update_summary("u2")
        summary = memory_store.get_performance_summary("u2")
        assert summary["avg_score"] == pytest.approx(0.65)
        assert "waves" in summary["weak_topics"]
        assert "kinematics" in summary["strong_topics"]

    def test_get_performance_summary_returns_default_for_unknown_user(self, memory_store: MemoryStore):
        summary = memory_store.get_performance_summary("unknown")
        assert summary["avg_score"] == 0.0
        assert summary["weak_topics"] == []
        assert summary["strong_topics"] == []
        assert summary["alert_flag"] is False

    def test_update_summary_sets_alert_flag_when_low_over_last_five(self, memory_store: MemoryStore):
        for _ in range(5):
            memory_store.append_assessment_result("u3", {"type": "quiz", "topic": "math", "score": 0.3})
        memory_store.update_summary("u3")
        summary = memory_store.get_performance_summary("u3")
        assert summary["alert_flag"] is True
        assert summary["avg_score"] == 0.3

    def test_update_summary_no_alert_when_few_results(self, memory_store: MemoryStore):
        memory_store.append_assessment_result("u4", {"type": "quiz", "topic": "math", "score": 0.2})
        memory_store.update_summary("u4")
        summary = memory_store.get_performance_summary("u4")
        assert summary["alert_flag"] is False

    def test_append_ignores_unknown_result_type(self, memory_store: MemoryStore):
        memory_store.append_assessment_result("u5", {"type": "other", "score": 0.5})
        memory_store.update_summary("u5")
        summary = memory_store.get_performance_summary("u5")
        assert summary["avg_score"] == 0.0


class TestContextManager:
    """Tests for ContextManager wrapping ContextStore."""

    def test_get_session_context_delegates_to_store(self, memory_store: MemoryStore):
        memory_store.set("s1", "k", "v")
        cm = ContextManager(memory_store)
        assert cm.get_session_context("s1") == {"k": "v"}
        assert cm.get_session_context("s1", key="k") == {"k": "v"}

    def test_get_session_context_empty_session_returns_empty(
        self, memory_store: MemoryStore
    ):
        cm = ContextManager(memory_store)
        assert cm.get_session_context("") == {}
        assert cm.get_session_context("missing") == {}

    def test_get_conversation_history_delegates_to_store(self, memory_store: MemoryStore):
        memory_store.append_message("s1", "user", "hello")
        cm = ContextManager(memory_store)
        hist = cm.get_conversation_history("s1")
        assert len(hist) == 1
        assert hist[0]["role"] == "user" and hist[0]["content"] == "hello"

    def test_persist_turn_appends_user_and_assistant(self, memory_store: MemoryStore):
        cm = ContextManager(memory_store)
        cm.persist_turn("s1", "user msg", "assistant msg")
        hist = memory_store.get_history("s1")
        assert len(hist) == 2
        assert hist[0]["role"] == "user" and hist[0]["content"] == "user msg"
        assert hist[1]["role"] == "assistant" and hist[1]["content"] == "assistant msg"

    def test_persist_turn_empty_session_id_no_op(self, memory_store: MemoryStore):
        cm = ContextManager(memory_store)
        cm.persist_turn("", "u", "a")
        assert memory_store.get_history("") == []

    def test_set_state_and_set_state_many(self, memory_store: MemoryStore):
        cm = ContextManager(memory_store)
        cm.set_state("s1", "k", "v")
        assert cm.get_session_context("s1") == {"k": "v"}
        cm.set_state_many("s1", {"a": 1, "b": 2})
        assert cm.get_session_context("s1") == {"k": "v", "a": 1, "b": 2}

    def test_delete_session(self, memory_store: MemoryStore):
        memory_store.set("s1", "x", 1)
        cm = ContextManager(memory_store)
        cm.delete_session("s1", key=None)
        assert memory_store.get("s1") == {}
