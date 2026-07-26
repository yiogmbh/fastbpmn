import asyncio
from asyncio import Queue
from uuid import uuid4

from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPISendCallable,
    ExternalTaskScope,
    AETPIReceiveEvent,
    AETPISendEvent,
    ExternalTaskEmitSignalEvent,
    ExternalTaskCorrelateMessageEvent,
    ExternalTaskVariableFetchEvent,
)
from pydantic import TypeAdapter

from fastbpmn.context import Context
from fastbpmn.context.exceptions import UnexpectedEventReceived, VariableFetchError
from fastbpmn.context.models import (
    Signal,
    SignalResult,
    Message,
    MessageResult,
    MessageFailure,
)
from fastbpmn.utils.asyncio import lock_decorator


message_adapter = TypeAdapter(MessageResult)


class ContextMiddleware:
    def __init__(self, app: AETPIApplication) -> None:
        self.app = app

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:

        if scope["type"] != "externaltask":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        lock = lock_decorator()
        receive_queue: Queue[AETPIReceiveEvent] = Queue()

        def from_queue() -> AETPIReceiveEvent | None:
            try:
                return receive_queue.get_nowait()
            except asyncio.QueueEmpty:
                return None

        async def receive_or_queue(
            type: str, transaction: str
        ) -> AETPIReceiveEvent | None:

            element = await receive()

            match element:
                case {"type": str(r_type), "transaction": str(r_transaction)} if (
                    r_type.startswith(type) and r_transaction == transaction
                ):
                    return element
                case _:
                    await receive_queue.put(element)

            return None

        @lock
        async def wrapped_send(event: AETPISendEvent) -> None:
            await send(event)

        @lock
        async def wrapped_receive() -> AETPIReceiveEvent:
            # first try returning items in queue, later try to receive with lock
            if (element := from_queue()) is not None:
                return element

            return await receive()

        @lock
        async def signal_emitter(signal: Signal) -> SignalResult:

            transaction = str(uuid4())
            send_event: ExternalTaskEmitSignalEvent = {
                "type": "externaltask.signal.emit",
                "transaction": transaction,
                "signal_name": signal.signal_name,
                "variables": signal.variables,
                "tenant_id": signal.tenant_id,
            }
            await send(send_event)

            while (
                element := await receive_or_queue("externaltask.signal.", transaction)
            ) is None:
                pass

            match element:
                case {"type": "externaltask.signal.emitted"}:
                    return SignalResult(success=True)
                case {
                    "type": "externaltask.signal.error",
                    "error_message": str(error_message),
                }:
                    return SignalResult(success=False, error_message=error_message)
                case _:
                    raise UnexpectedEventReceived()

        @lock
        async def message_correlator(
            message: Message,
        ) -> MessageResult | MessageFailure:

            transaction = str(uuid4())
            send_event: ExternalTaskCorrelateMessageEvent = {
                "type": "externaltask.message.correlate",
                "transaction": transaction,
                "message_name": message.message_name,
                "business_key": message.business_key,
                "process_instance_id": message.process_instance_id,
                "tenant_id": message.tenant_id,
                "variables": message.variables,
                "local_variables": message.local_variables,
                "scoped_variables": message.scoped_variables,
                "multicast": message.multicast,
            }
            await send(send_event)

            while (
                element := await receive_or_queue("externaltask.message.", transaction)
            ) is None:
                pass

            match element:
                case {
                    "type": "externaltask.message.delivered",
                }:
                    # probably use pydantic type adapter to map that objects here
                    return message_adapter.validate_python(element)
                case {
                    "type": "externaltask.message.error",
                    "error_message": str(error_message),
                }:
                    return MessageFailure(error_message=error_message)
                case _:
                    raise UnexpectedEventReceived()

        @lock
        async def variable_fetcher(variable_name: str, file_path: str) -> None:
            transaction = str(uuid4())
            send_event: ExternalTaskVariableFetchEvent = {
                "type": "externaltask.variable.fetch",
                "transaction": transaction,
                "variable_name": variable_name,
                "file_path": file_path,
            }
            await send(send_event)

            while (
                element := await receive_or_queue(
                    "externaltask.variable.fetch.", transaction
                )
            ) is None:
                pass

            match element:
                case {"type": "externaltask.variable.fetch.completed"}:
                    return
                case {
                    "type": "externaltask.variable.fetch.failed",
                    "error_message": str(error_message),
                }:
                    raise VariableFetchError(
                        error_message,
                        variable_name=variable_name,
                        file_path=file_path,
                    )
                case _:
                    raise UnexpectedEventReceived()

        async with Context(
            variable_fetcher=variable_fetcher,
            message_correlator=message_correlator,
            signal_emitter=signal_emitter,
        ) as context:
            scope["context"] = context

            await self.app(scope, wrapped_receive, wrapped_send)
