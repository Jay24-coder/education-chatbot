"""Unit tests for orchestrator intent classification and request validation."""

import pytest

from app.orchestrator.orchestrator_agent import (
    classify_intent,
    validate_and_sanitize_request,
)
from app.orchestrator.types import Intent, UserRequest
from app.utils.errors import ValidationError


class TestClassifyIntent:
    """Tests for classify_intent(message) -> Intent."""

    def test_syllabus_keywords(self):
        assert classify_intent("What is the syllabus?") == Intent.SYLLABUS
        assert classify_intent("curriculum overview") == Intent.SYLLABUS
        assert classify_intent("prerequisites for the course") == Intent.SYLLABUS
        assert classify_intent("topics covered") == Intent.SYLLABUS

    def test_admin_keywords(self):
        assert classify_intent("When is the deadline?") == Intent.ADMIN
        assert classify_intent("attendance policy") == Intent.ADMIN
        assert classify_intent("how do I submit the assignment?") == Intent.ADMIN
        assert classify_intent("grade appeal procedure") == Intent.ADMIN

    def test_topic_keywords(self):
        assert classify_intent("Explain the concept of variables") == Intent.TOPIC
        assert classify_intent("what is a function?") == Intent.TOPIC
        assert classify_intent("how does recursion work?") == Intent.TOPIC
        assert classify_intent("definition of algorithm") == Intent.TOPIC

    def test_unknown_empty(self):
        assert classify_intent("") == Intent.UNKNOWN

    def test_unknown_whitespace_only(self):
        assert classify_intent("   \n\t  ") == Intent.UNKNOWN

    def test_unknown_unrelated(self):
        assert classify_intent("hello world") == Intent.UNKNOWN
        assert classify_intent("what's the weather?") == Intent.UNKNOWN

    def test_normalization_lowercase(self):
        assert classify_intent("SYLLABUS") == Intent.SYLLABUS
        assert classify_intent("DEADLINE") == Intent.ADMIN


class TestValidateAndSanitizeRequest:
    """Tests for validate_and_sanitize_request(UserRequest)."""

    def test_valid_request_passes_through(self):
        req = UserRequest(message="What is the syllabus?")
        out = validate_and_sanitize_request(req)
        assert out.message == "What is the syllabus?"
        assert out.session_id is None

    def test_strips_whitespace(self):
        req = UserRequest(message="  hello  ")
        out = validate_and_sanitize_request(req)
        assert out.message == "hello"

    def test_empty_after_strip_raises(self):
        req = UserRequest(message="   ")
        with pytest.raises(ValidationError) as exc_info:
            validate_and_sanitize_request(req)
        assert exc_info.value.code == "EMPTY_MESSAGE"

    def test_message_too_long_raises(self):
        req = UserRequest(message="x" * 33_000)
        with pytest.raises(ValidationError) as exc_info:
            validate_and_sanitize_request(req)
        assert exc_info.value.code == "MESSAGE_TOO_LONG"

    def test_preserves_session_and_correlation_id(self):
        req = UserRequest(
            message="hi",
            session_id="s1",
            correlation_id="c1",
        )
        out = validate_and_sanitize_request(req)
        assert out.session_id == "s1"
        assert out.correlation_id == "c1"
