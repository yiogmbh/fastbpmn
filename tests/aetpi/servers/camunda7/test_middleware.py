from unittest.mock import AsyncMock

import pytest

from fastbpmn.aetpi.servers.camunda7.middleware import Camunda7VariablePreprocessor


def make_send_capturer(captured: dict):
    async def send(event: dict) -> None:
        captured.clear()
        captured.update(event)

    return send


@pytest.mark.asyncio
async def test_execute_complete_variables_encoded():
    captured = {}
    inner_app = AsyncMock()
    middleware = Camunda7VariablePreprocessor(inner_app)
    scope = {"type": "externaltask"}
    receive = AsyncMock()
    send = make_send_capturer(captured)

    async def inner_impl(scope, receive, send):
        await send(
            {
                "type": "externaltask.execute.complete",
                "variables": {"str_var": "hello", "num_var": 42},
            }
        )

    inner_app.side_effect = inner_impl
    await middleware(scope, receive, send)

    assert captured["type"] == "externaltask.execute.complete"
    for v in captured["variables"].values():
        assert "type" in v
        assert "value" in v


@pytest.mark.asyncio
async def test_execute_complete_local_variables_encoded():
    captured = {}
    inner_app = AsyncMock()
    middleware = Camunda7VariablePreprocessor(inner_app)
    scope = {"type": "externaltask"}
    receive = AsyncMock()
    send = make_send_capturer(captured)

    async def inner_impl(scope, receive, send):
        await send(
            {
                "type": "externaltask.execute.complete",
                "variables": {"global": "g"},
                "local_variables": {"local": "l"},
            }
        )

    inner_app.side_effect = inner_impl
    await middleware(scope, receive, send)

    assert captured["type"] == "externaltask.execute.complete"
    for v in captured["variables"].values():
        assert "type" in v
        assert "value" in v
    for v in captured["local_variables"].values():
        assert "type" in v
        assert "value" in v


@pytest.mark.asyncio
async def test_execute_complete_mixed_encoding():
    captured = {}
    inner_app = AsyncMock()
    middleware = Camunda7VariablePreprocessor(inner_app)
    scope = {"type": "externaltask"}
    receive = AsyncMock()
    send = make_send_capturer(captured)

    async def inner_impl(scope, receive, send):
        await send(
            {
                "type": "externaltask.execute.complete",
                "variables": None,
                "local_variables": {"only_local": True},
            }
        )

    inner_app.side_effect = inner_impl
    await middleware(scope, receive, send)

    assert captured["variables"] is None
    assert "local_variables" in captured
    for v in captured["local_variables"].values():
        assert "type" in v
        assert "value" in v
