from unittest.mock import AsyncMock

import pytest

from fastbpmn.aetpi.middleware.variables import BaseSyncVariableHandlerMiddleware


class RecordingMiddleware(BaseSyncVariableHandlerMiddleware):
    """Middleware that records calls for inspection."""

    def __init__(self, app):
        super().__init__(app)
        self.application_calls = []
        self.server_calls = []

    def process_application_variables(self, variables):
        self.application_calls.append(variables)
        return (
            {f"app_{k}": v for k, v in (variables or {}).items()} if variables else None
        )

    def process_server_variables(self, variables):
        self.server_calls.append(variables)
        return (
            {f"srv_{k}": v for k, v in (variables or {}).items()} if variables else None
        )


@pytest.mark.asyncio
async def test_send_wrapper_execute_complete_with_local_variables():
    inner_app = AsyncMock()
    middleware = RecordingMiddleware(inner_app)
    scope = {"type": "externaltask"}
    receive = AsyncMock()

    async def send(event):
        pass

    async def inner_app_impl(scope, receive, send):
        await send(
            {
                "type": "externaltask.execute.complete",
                "variables": {"a": 1},
                "local_variables": {"b": 2},
            }
        )

    inner_app.side_effect = inner_app_impl

    await middleware(scope, receive, send)

    assert middleware.server_calls == [{"a": 1}, {"b": 2}]


@pytest.mark.asyncio
async def test_send_wrapper_execute_complete_without_local_variables():
    inner_app = AsyncMock()
    middleware = RecordingMiddleware(inner_app)
    scope = {"type": "externaltask"}
    receive = AsyncMock()

    async def send(event):
        pass

    async def inner_app_impl(scope, receive, send):
        await send(
            {
                "type": "externaltask.execute.complete",
                "variables": {"a": 1},
            }
        )

    inner_app.side_effect = inner_app_impl

    await middleware(scope, receive, send)

    assert middleware.server_calls == [{"a": 1}]


@pytest.mark.asyncio
async def test_send_wrapper_execute_complete_no_variables_at_all():
    inner_app = AsyncMock()
    middleware = RecordingMiddleware(inner_app)
    scope = {"type": "externaltask"}
    receive = AsyncMock()
    captured = {}

    async def send(event):
        captured.update(event)

    async def inner_app_impl(scope, receive, send):
        await send(
            {
                "type": "externaltask.execute.complete",
                "variables": None,
            }
        )

    inner_app.side_effect = inner_app_impl

    await middleware(scope, receive, send)

    assert captured["variables"] is None


@pytest.mark.asyncio
async def test_send_wrapper_execute_complete_local_variables_processed():
    inner_app = AsyncMock()
    middleware = RecordingMiddleware(inner_app)
    scope = {"type": "externaltask"}
    receive = AsyncMock()
    captured = {}

    async def send(event):
        captured.update(event)

    async def inner_app_impl(scope, receive, send):
        await send(
            {
                "type": "externaltask.execute.complete",
                "variables": {"a": 1},
                "local_variables": {"b": 2},
            }
        )

    inner_app.side_effect = inner_app_impl

    await middleware(scope, receive, send)

    assert captured["variables"] == {"srv_a": 1}
    assert captured["local_variables"] == {"srv_b": 2}
