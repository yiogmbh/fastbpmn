from asyncio import Queue
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from aetpiref.typing import TENANT_UNSPECIFIED

from fastbpmn.context import Context
from fastbpmn.context.exceptions import (
    MessageCorrelateError,
    SignalFailureError,
    UnexpectedEventReceived,
)
from fastbpmn.context.models import Message, MessageResult, Signal
from fastbpmn.middleware.context import ContextMiddleware


@pytest.fixture()
async def receive_queue() -> Queue:
    return Queue()


@pytest.fixture()
def make_receive(receive_queue: Queue):
    async def _receive():
        return await receive_queue.get()

    return _receive


DEFAULT_SCOPE = {
    "type": "externaltask",
    "protocol": "camunda7",
    "aetpi": {"spec_version": "1.0", "version": "1.0"},
    "task": {
        "id": "test-task",
        "activity_id": None,
        "activity_instance_id": None,
        "execution_id": None,
        "error_message": None,
        "business_key": None,
        "topic_name": "test-topic",
        "process_definition_id": None,
        "process_definition_key": None,
        "process_definition_version_tag": None,
        "process_instance_id": None,
        "tenant_id": None,
        "retries": None,
        "suspended": False,
        "priority": None,
        "worker_id": None,
        "lock_expiration_time": None,
        "retry_timeout": None,
        "lock_duration": None,
        "title": None,
        "description": None,
    },
    "x_download_file_var": AsyncMock(),
}


@pytest.mark.asyncio
async def test_passthrough_non_externaltask():
    scope = {"type": "http"}
    receive = AsyncMock()
    send = AsyncMock()
    inner_app = AsyncMock()

    middleware = ContextMiddleware(inner_app)
    await middleware(scope, receive, send)

    inner_app.assert_awaited_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_context_injected_into_scope():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    received_events = []

    async def receive():
        return await receive_queue.get()

    async def send(event):
        pass

    async def inner_app(scope, receive, send):
        assert "context" in scope
        assert isinstance(scope["context"], Context)
        received_events.append("inner_called")

    middleware = ContextMiddleware(inner_app)
    await middleware(scope, receive, send)

    assert received_events == ["inner_called"]


@pytest.mark.asyncio
async def test_signal_emission_success():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "externaltask.signal.emitted",
            "transaction": "fixed-txn",
        }
    )
    send = AsyncMock()

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        await context.emit_signal(Signal(signal_name="test-signal"))

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)

    send.assert_any_call(
        {
            "type": "externaltask.signal.emit",
            "transaction": "fixed-txn",
            "signal_name": "test-signal",
            "variables": None,
            "tenant_id": TENANT_UNSPECIFIED,
        }
    )


@pytest.mark.asyncio
async def test_signal_emission_error():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "externaltask.signal.error",
            "transaction": "fixed-txn",
            "error_message": "something went wrong",
        }
    )
    send = AsyncMock()

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        with pytest.raises(SignalFailureError, match="something went wrong"):
            await context.emit_signal(Signal(signal_name="test-signal"))

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)


@pytest.mark.asyncio
async def test_signal_emission_unexpected_event():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "externaltask.signal.unknown",
            "transaction": "fixed-txn",
        }
    )
    send = AsyncMock()

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        with pytest.raises(UnexpectedEventReceived):
            await context.emit_signal(Signal(signal_name="test-signal"))

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)


@pytest.mark.asyncio
async def test_message_correlation_success():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "externaltask.message.delivered",
            "transaction": "fixed-txn",
            "recipients": [],
        }
    )
    send = AsyncMock()

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        result = await context.correlate_message(Message(message_name="test-message"))
        assert isinstance(result, MessageResult)
        assert result.recipients == []

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)

    send.assert_any_call(
        {
            "type": "externaltask.message.correlate",
            "transaction": "fixed-txn",
            "message_name": "test-message",
            "business_key": None,
            "process_instance_id": None,
            "tenant_id": TENANT_UNSPECIFIED,
            "variables": None,
            "local_variables": None,
            "scoped_variables": None,
            "multicast": True,
        }
    )


@pytest.mark.asyncio
async def test_message_correlation_error():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "externaltask.message.error",
            "transaction": "fixed-txn",
            "error_message": "delivery failed",
        }
    )
    send = AsyncMock()

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        with pytest.raises(MessageCorrelateError, match="delivery failed"):
            await context.correlate_message(Message(message_name="test-message"))

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)


@pytest.mark.asyncio
async def test_message_correlation_unexpected_event():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "externaltask.message.unknown",
            "transaction": "fixed-txn",
        }
    )
    send = AsyncMock()

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        with pytest.raises(UnexpectedEventReceived):
            await context.correlate_message(Message(message_name="test-message"))

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)


@pytest.mark.asyncio
async def test_unrelated_events_queued_during_signal():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "some.unrelated.event",
            "transaction": "other-txn",
        }
    )
    await receive_queue.put(
        {
            "type": "externaltask.signal.emitted",
            "transaction": "fixed-txn",
        }
    )
    send = AsyncMock()
    post_signal_events = []

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        await context.emit_signal(Signal(signal_name="test-signal"))

        queued_event = await receive()
        post_signal_events.append(queued_event)

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)

    assert post_signal_events == [
        {"type": "some.unrelated.event", "transaction": "other-txn"},
    ]


@pytest.mark.asyncio
async def test_unrelated_events_queued_during_message():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    await receive_queue.put(
        {
            "type": "some.unrelated.event",
            "transaction": "other-txn",
        }
    )
    await receive_queue.put(
        {
            "type": "externaltask.message.delivered",
            "transaction": "fixed-txn",
            "recipients": [],
        }
    )
    send = AsyncMock()
    post_message_events = []

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        await context.correlate_message(Message(message_name="test-message"))

        queued_event = await receive()
        post_message_events.append(queued_event)

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)

    assert post_message_events == [
        {"type": "some.unrelated.event", "transaction": "other-txn"},
    ]


@pytest.mark.asyncio
async def test_message_result_validated_via_pydantic():
    scope = dict(DEFAULT_SCOPE)
    receive_queue: Queue = Queue()
    recipient = {
        "type": "start_event",
        "process_instance": {
            "id": "pi-1",
            "definition_id": "d-1",
            "business_key": "bk-1",
            "tenant_id": None,
        },
        "execution": None,
        "variables": None,
    }
    await receive_queue.put(
        {
            "type": "externaltask.message.delivered",
            "transaction": "fixed-txn",
            "recipients": [recipient],
        }
    )
    send = AsyncMock()
    result_holder = []

    async def receive():
        return await receive_queue.get()

    async def inner_app(scope, receive, send):
        context = scope["context"]
        result = await context.correlate_message(Message(message_name="test-message"))
        result_holder.append(result)

    middleware = ContextMiddleware(inner_app)

    with mock.patch("fastbpmn.middleware.context.uuid4", return_value="fixed-txn"):
        await middleware(scope, receive, send)

    assert len(result_holder) == 1
    result = result_holder[0]
    assert isinstance(result, MessageResult)
    assert len(result.recipients) == 1
    r = result.recipients[0]
    assert r.type == "start_event"
    assert r.process_instance is not None
    assert r.process_instance.id == "pi-1"
    assert r.process_instance.definition_id == "d-1"
    assert r.process_instance.business_key == "bk-1"
