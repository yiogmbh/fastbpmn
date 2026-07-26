from unittest.mock import AsyncMock

import pytest

from fastbpmn.result import SuccessResult


@pytest.mark.asyncio
async def test_success_result_default():
    scope = {"type": "externaltask", "task": {}}
    receive = AsyncMock()
    send = AsyncMock()

    result = SuccessResult()
    await result(scope, receive, send)

    send.assert_awaited_once_with(
        {
            "type": "externaltask.execute.complete",
            "variables": None,
            "local_variables": None,
        }
    )


@pytest.mark.asyncio
async def test_success_result_with_variables():
    scope = {"type": "externaltask", "task": {}}
    receive = AsyncMock()
    send = AsyncMock()

    result = SuccessResult(variables={"key": "value"})
    await result(scope, receive, send)

    args, _ = send.call_args
    event = args[0]
    assert event["type"] == "externaltask.execute.complete"
    assert event["variables"] == {"key": "value"}
    assert "local_variables" in event


@pytest.mark.asyncio
async def test_success_result_with_local_variables():
    scope = {"type": "externaltask", "task": {}}
    receive = AsyncMock()
    send = AsyncMock()

    result = SuccessResult(
        variables={"key": "value"},
        local_variables={"local_key": "local_value"},
    )
    await result(scope, receive, send)

    args, _ = send.call_args
    event = args[0]
    assert event["type"] == "externaltask.execute.complete"
    assert event["variables"] == {"key": "value"}
    assert event["local_variables"] == {"local_key": "local_value"}


@pytest.mark.asyncio
async def test_success_result_with_only_local_variables():
    scope = {"type": "externaltask", "task": {}}
    receive = AsyncMock()
    send = AsyncMock()

    result = SuccessResult(local_variables={"local_key": "local_value"})
    await result(scope, receive, send)

    args, _ = send.call_args
    event = args[0]
    assert event["type"] == "externaltask.execute.complete"
    assert event["variables"] is None
    assert event["local_variables"] == {"local_key": "local_value"}
