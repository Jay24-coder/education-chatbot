import asyncio

import pytest

from app.agents.shared_tools.code_execution import (
    CodeExecutionTimeoutError,
    UnsafeCodeError,
    execute_in_docker,
)


@pytest.mark.asyncio
async def test_execute_in_docker_hello_world():
    code = 'print("hello world")'

    # Use a longer timeout to allow for Docker startup in slow environments
    result = await execute_in_docker(code=code, language="python", timeout_seconds=15.0)

    assert result.all_passed is True
    assert "hello world" in result.stdout
    assert result.error is None


@pytest.mark.asyncio
async def test_execute_in_docker_timeout_for_infinite_loop():
    code = "while True:\n    pass"

    with pytest.raises(CodeExecutionTimeoutError):
        await execute_in_docker(code=code, language="python", timeout_seconds=0.5)


@pytest.mark.asyncio
async def test_execute_in_docker_unsafe_code_raises_error():
    # This uses an obviously unsafe pattern that our pre-check should catch.
    code = "import os\nos.system('echo dangerous')"

    with pytest.raises(UnsafeCodeError):
        await execute_in_docker(code=code, language="python", timeout_seconds=5.0)

