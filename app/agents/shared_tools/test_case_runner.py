from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

from .programming_bank import ProgrammingChallenge, ProgrammingTestCase


@dataclass(slots=True)
class CaseRunResult:
    """
    Result of executing a single test case.
    """

    test_case: ProgrammingTestCase
    passed: bool
    actual_output: Optional[str]
    expected_output: Optional[str]
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


@dataclass(slots=True)
class ExecutionResult:
    """
    Aggregate result of executing all test cases for a challenge.
    """

    test_results: List[CaseRunResult]
    all_passed: bool
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


ExecutorCallable = Callable[[str, str, float], Awaitable[ExecutionResult]]


def _extract_function_name(function_signature: str) -> str:
    """
    Extract the function name from a Python function signature string.

    Example:
        "def add(a: int, b: int) -> int:" -> "add"
    """
    signature = function_signature.strip()
    if not signature.startswith("def "):
        raise ValueError(f"Unsupported function signature format: {function_signature!r}")

    # Remove leading "def " and take up to the first "(".
    name_and_rest = signature[4:]
    name_end = name_and_rest.find("(")
    if name_end == -1:
        raise ValueError(f"Unsupported function signature format: {function_signature!r}")
    return name_and_rest[:name_end].strip()


async def run_test_cases(
    challenge: ProgrammingChallenge,
    code: str,
    executor: ExecutorCallable,
    timeout_seconds: float = 3.0,
) -> List[CaseRunResult]:
    """
    Execute a student's solution against all test cases for the given challenge.

    This function is intentionally generic: it knows how to:
    - wrap the student's code with a small harness that calls the expected function
      using each test case's input; and
    - interpret the sandbox execution result into per-test-case CaseRunResult objects.
    """
    function_name = _extract_function_name(challenge.function_signature)

    results: List[CaseRunResult] = []

    for test_case in challenge.test_cases:
        # The test case input is expected to be a Python argument list such as:
        # "1, 2" or "'abc'" or "[1, 2, 3]".
        harness = "\n".join(
            [
                code.rstrip(),
                "",
                "if __name__ == '__main__':",
                f"    result = {function_name}({test_case.input})",
                "    print(result)",
            ]
        )

        execution = await executor(harness, challenge.language, timeout_seconds)

        # For now, we treat stdout as the "actual output" and compare it to the
        # expected output as a string. Callers can choose to normalize further
        # (e.g. strip whitespace) if desired.
        actual_output = (execution.stdout or "").strip()
        expected_output = (test_case.expected_output or "").strip()

        passed = (
            execution.error is None
            and not execution.stderr
            and actual_output == expected_output
        )

        error_message = execution.error or (execution.stderr or None)

        results.append(
            CaseRunResult(
                test_case=test_case,
                passed=passed,
                actual_output=actual_output,
                expected_output=test_case.expected_output,
                error=error_message,
                execution_time_ms=None,
            )
        )

    return results

