from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(slots=True)
class ProgrammingTestCase:
    """
    Canonical description of a single programming test case.
    """

    id: str
    input: str
    expected_output: str
    is_hidden: bool = False


@dataclass(slots=True)
class ProgrammingChallenge:
    """
    Canonical description of a programming challenge used across agents.
    """

    id: str
    title: str
    description: str
    function_signature: str
    language: str
    difficulty: str
    topic: str
    test_cases: List[ProgrammingTestCase]


class ProgrammingQuestionBank:
    """
    Lightweight question bank wrapper for programming challenges.

    Provides a stable interface for agents to retrieve challenges without
    depending on the internal storage representation.
    """

    def __init__(self, challenges: Sequence[ProgrammingChallenge] | None = None) -> None:
        self._challenges: List[ProgrammingChallenge] = list(challenges) if challenges is not None else list(_CHALLENGES)

    def get_challenge(self, topic: str | None, difficulty: str | None) -> ProgrammingChallenge:
        return get_challenge(topic, difficulty)


def _build_sum_two_numbers_challenge() -> ProgrammingChallenge:
    return ProgrammingChallenge(
        id="sum_two_numbers",
        title="Sum two numbers",
        description="Implement a function that returns the sum of two integers.",
        function_signature="def sum_two_numbers(a: int, b: int) -> int:",
        language="python",
        difficulty="beginner",
        topic="math",
        test_cases=[
            ProgrammingTestCase(id="t1", input="1, 2", expected_output="3"),
            ProgrammingTestCase(id="t2", input="-1, 1", expected_output="0"),
            ProgrammingTestCase(id="t3", input="100, 200", expected_output="300"),
            ProgrammingTestCase(id="t4", input="0, 0", expected_output="0", is_hidden=True),
        ],
    )


def _build_reverse_string_challenge() -> ProgrammingChallenge:
    return ProgrammingChallenge(
        id="reverse_string",
        title="Reverse a string",
        description="Implement a function that returns the reverse of the input string.",
        function_signature="def reverse_string(s: str) -> str:",
        language="python",
        difficulty="beginner",
        topic="strings",
        test_cases=[
            ProgrammingTestCase(id="t1", input="'abc'", expected_output="cba"),
            ProgrammingTestCase(id="t2", input="'racecar'", expected_output="racecar"),
            ProgrammingTestCase(id="t3", input="'hello'", expected_output="olleh"),
            ProgrammingTestCase(id="t4", input="'',", expected_output="", is_hidden=True),
        ],
    )


def _build_max_in_list_challenge() -> ProgrammingChallenge:
    return ProgrammingChallenge(
        id="max_in_list",
        title="Maximum in a list",
        description="Implement a function that returns the maximum element in a list of integers.",
        function_signature="def max_in_list(values: list[int]) -> int:",
        language="python",
        difficulty="intermediate",
        topic="arrays",
        test_cases=[
            ProgrammingTestCase(id="t1", input="[1, 2, 3]", expected_output="3"),
            ProgrammingTestCase(id="t2", input="[-5, -1, -10]", expected_output="-1"),
            ProgrammingTestCase(id="t3", input="[42]", expected_output="42"),
            ProgrammingTestCase(id="t4", input="[0, 0, 0]", expected_output="0", is_hidden=True),
        ],
    )


_CHALLENGES: List[ProgrammingChallenge] = [
    _build_sum_two_numbers_challenge(),
    _build_reverse_string_challenge(),
    _build_max_in_list_challenge(),
]


def get_challenge(topic: str | None, difficulty: str | None) -> ProgrammingChallenge:
    """
    Retrieve a programming challenge by optional topic and difficulty.

    The selection is deterministic: the first matching challenge is returned.
    """
    candidates: Sequence[ProgrammingChallenge] = _CHALLENGES

    if topic is not None:
        candidates = [c for c in candidates if c.topic == topic]

    if difficulty is not None:
        candidates = [c for c in candidates if c.difficulty == difficulty]

    if not candidates:
        raise ValueError(f"No programming challenge found for topic={topic!r}, difficulty={difficulty!r}.")

    return candidates[0]


