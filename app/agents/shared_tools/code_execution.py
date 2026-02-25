from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from .test_case_runner import ExecutionResult


class UnsafeCodeError(Exception):
    """Raised when the submitted code violates safety policies."""


class CodeExecutionTimeoutError(Exception):
    """Raised when code execution exceeds the configured timeout."""


class SandboxError(Exception):
    """Raised for infrastructure or sandbox-level failures."""


def _ensure_safe_code(code: str) -> None:
    """
    Perform a lightweight, best-effort static check to reject obviously unsafe code.

    This is not a full sandbox, but it helps catch the most common attempts to
    break isolation before we even invoke Docker.
    """
    banned_patterns = [
        "import os",
        "from os",
        "import subprocess",
        "from subprocess",
        "import socket",
        "from socket",
        "__import__(",
        "open(",
        "eval(",
        "exec(",
    ]
    lowered = code.lower()
    for pattern in banned_patterns:
        if pattern in lowered:
            raise UnsafeCodeError(f"Unsafe code pattern detected: {pattern}")


async def _run_docker_process(command: list[str], timeout_seconds: float) -> tuple[int, str, str]:
    """
    Run a Docker command asynchronously with a timeout, returning (exit_code, stdout, stderr).
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
            raise CodeExecutionTimeoutError(
                f"Code execution exceeded timeout of {timeout_seconds} seconds."
            ) from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return process.returncode, stdout, stderr
    except FileNotFoundError as exc:
        # Docker CLI not available
        raise SandboxError("Docker executable not found on host.") from exc


async def execute_in_docker(code: str, language: str, timeout_seconds: float) -> ExecutionResult:
    """
    Execute student code inside a short-lived Docker container and return an ExecutionResult.

    For Phase 3, only Python is supported. Callers are responsible for interpreting stdout/stderr
    and mapping them onto per-test-case results if needed.
    """
    _ensure_safe_code(code)

    if language.lower() != "python":
        raise SandboxError(f"Unsupported language '{language}'. Only Python is allowed in Phase 3.")

    # Write the user's code to a temporary directory that will be mounted into the container.
    with tempfile.TemporaryDirectory(prefix="edu-sandbox-") as tmp_dir:
        host_dir = Path(tmp_dir)
        script_path = host_dir / "main.py"
        script_path.write_text(code, encoding="utf-8")

        docker_image = "python:3.13-slim"

        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cpus",
            "1.0",
            "--memory",
            "512m",
            "--pids-limit",
            "64",
            "-v",
            f"{host_dir.as_posix()}:/workspace:ro",
            "-w",
            "/workspace",
            docker_image,
            "python",
            "main.py",
        ]

        exit_code, stdout, stderr = await _run_docker_process(command, timeout_seconds=timeout_seconds)

        if exit_code != 0:
            # At this layer we do not know which test failed; callers can inspect stderr/stdout.
            return ExecutionResult(
                test_results=[],
                all_passed=False,
                stdout=stdout,
                stderr=stderr,
                error=f"Sandboxed execution failed with exit code {exit_code}.",
            )

        return ExecutionResult(
            test_results=[],
            all_passed=True,
            stdout=stdout,
            stderr=stderr,
            error=None,
        )


