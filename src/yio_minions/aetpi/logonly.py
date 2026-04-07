import asyncio
import logging
import uuid
from asyncio import Queue
from pathlib import Path
from random import choice
from typing import TYPE_CHECKING
from uuid import UUID

import pydantic.v1
from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPISendCallable,
    ExternalTaskScope,
    TaskScope,
)

from yio_minions.aetpi import protocol as event
from yio_minions.aetpi import utils

if TYPE_CHECKING:
    from yio_minions.context import Context

logger = logging.getLogger(__name__)
# An AETPI protocol implementation that does nothing but log the events
# and sometimes sleep a little bit


class LogOnlyExternalTaskProcessor:
    """
    External Task Processor for Camunda 7
    """

    def __init__(
        self,
    ):
        self._lock_duration = 10000

    async def _handle_lock_request(
        self, _event: event.ExternalTaskLockRequestEvent, send: AETPISendCallable
    ) -> None:
        """
        Handle the lock request
        """
        if bool(choice([True, True, True, False])):
            await send(utils.create_event_lock_accept(self._lock_duration))
        else:
            await send(
                utils.create_event_lock_reject(
                    "CUSTOM", "Flipped the coin ... and I don't want to"
                )
            )

    async def _handle_execute_request(
        self, _event: event.ExternalTaskExecuteRequestEvent, send: AETPISendCallable
    ) -> None:
        """
        Handle the execute request
        """
        if bool(choice([True, True, True, False])):
            await send(utils.create_event_execute_accept())
        else:
            await send(
                utils.create_event_execute_reject(
                    "CUSTOM", "Flipped the coin ... and I don't want to"
                )
            )

    async def simulate_work(self, _event: event.ExternalTaskExecuteStartEvent):

        class VarsV1(pydantic.v1.BaseModel):
            x: int
            y: int
            z: int

        class VarsV2(pydantic.BaseModel):
            x: int
            y: int
            z: int
            sub_guid: UUID = pydantic.Field(default_factory=uuid.uuid4)

            @pydantic.computed_field
            def path_to_var(self) -> Path:
                return Path(__file__).parent

            @pydantic.computed_field
            def sum(self) -> int:
                return self.x + self.y + self.z

        class Test:
            def __init__(self, x: int, y: int, z: int):
                self.x = x
                self.y = y
                self.z = z

        class OutputModel(pydantic.BaseModel):
            vars_v2: VarsV2

            guid: UUID = pydantic.Field(default_factory=uuid.uuid4)

            @pydantic.computed_field
            def sum_v2(self) -> int:
                return self.vars_v2.x + self.vars_v2.y + self.vars_v2.z

            @pydantic.computed_field
            def path_to_var(self) -> Path:
                return Path(__file__)

        class InputModel(pydantic.BaseModel):
            x: int
            y: int
            z: int

        input_model = InputModel(**_event["variables"])
        _ = VarsV1(**input_model.model_dump(mode="python"))
        vars_v2 = VarsV2(**input_model.model_dump(mode="python"))

        output_model = OutputModel(vars_v2=vars_v2)

        all_values = output_model.model_dump(mode="python")
        all_values.update(dict(output_model))

        return output_model.model_dump(mode="python")

    async def _handle_execute_start_event(
        self,
        _task_scope: TaskScope,
        _event: event.ExternalTaskExecuteStartEvent,
        send: AETPISendCallable,
    ):
        """
        Handle the execute start event
        """

        match choice([0, 0, 0, 0, 1, 2]):
            case 0:
                logger.info(f"Doing things for {_task_scope} - {_event}")
                await asyncio.sleep((self._lock_duration / 4) / 1000)

                result = await self.simulate_work(_event)

                await send(utils.create_event_execute_complete(variables=result))
            case 1:
                await send(
                    utils.create_event_execute_failure(
                        error_message="I don't like the color of the sky today",
                        error_details="The error was random ... please try again later",
                        variables={"error": "random", "location": Path(__file__)},
                    )
                )
            case _:
                await send(
                    utils.create_event_execute_business_error(
                        error_code="business_error_101",
                        error_message="Processes are here to face with errors as well",
                        variables={"error": "business", "location": Path(__file__)},
                    )
                )

    async def __call__(
        self,
        scope: ExternalTaskScope,
        context: "Context",
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        """
        Process the external task
        """
        # Check if the protocol is supported
        if scope["type"] != "externaltask":  # pragma: no cover
            await self.app(scope, context, receive, send)
            return

        # The tasks properties are crucial so lets extract them now
        task_scope: TaskScope = scope.get("task")

        while (event := await receive()) is not None:
            # a more sophisticated implementation would use a state machine
            # and check if the event is valid in the current state
            # but for testing thats ok.
            match event:
                case {"type": "externaltask.start"}:
                    logger.info(f"External Task started: {task_scope}")
                case {"type": "externaltask.lock.request"}:
                    logger.info(f"External Task lock request: {task_scope}")
                    await self._handle_lock_request(event, send)
                case {"type": "externaltask.execute.request"}:
                    logger.info(f"External Task execute request: {task_scope}")
                    await self._handle_execute_request(event, send)
                case {"type": "externaltask.execute.start"}:
                    logger.info(f"External Task execute start: {task_scope}")
                    await self._handle_execute_start_event(task_scope, event, send)
                case {"type": "externaltask.end"}:
                    logger.info(f"External Task end: {task_scope}")
                    break
                case _:
                    logger.warning(f"Unexpected event: {event}")


async def server(app: AETPIApplication, topic: str):
    send_queue: Queue[event.AETPIReceiveEvent] = Queue()

    # First indicate the start of an arbitrary external task
    await send_queue.put(utils.create_event_start())
    await send_queue.put(utils.create_event_lock_request())

    async def receive() -> event.AETPIReceiveEvent:
        return await send_queue.get()

    # The send callable is actually where get the responses from

    async def send(event: event.AETPISendEvent) -> None:

        match event:
            case {"type": "externaltask.lock.accept"}:
                logger.info("<server-receive> Lock accepted")
                logger.info(event)
                await send_queue.put(utils.create_event_execute_request())
            case {"type": "externaltask.execute.accept"}:
                logger.info("<server-receive> Execute accepted")
                logger.info(event)
                await send_queue.put(
                    utils.create_event_execute_start({"x": 1, "y": 2, "z": 3})
                )
            case {"type": "externaltask.execute.complete"}:
                logger.info("Execute complete")
                logger.info(event)
                await send_queue.put(utils.create_event_end())

            case {"type": "externaltask.lock.reject"}:
                logger.info("Lock rejected")
                logger.info(event)
                await send_queue.put(utils.create_event_end())
            case {"type": "externaltask.execute.reject"}:
                logger.info("Execute rejected")
                logger.info(event)
                await send_queue.put(utils.create_event_end())
            case {"type": "externaltask.execute.failure"}:
                logger.info("Execute failure")
                logger.info(event)
                await send_queue.put(utils.create_event_end())
            case {"type": "externaltask.execute.error"}:
                logger.info("Execute business error")
                logger.info(event)
                await send_queue.put(utils.create_event_end())
            case _:
                logger.info(event)
                logger.warning(f"Unexpected event: {event}")

    await app(
        {
            "type": "externaltask",
            "protocol": "camunda7",
            "aetpi": {"version": "1.0", "spec_version": "1.0"},
            "task": {"id": "12345678-1234-5678-1234-567812345678", "topic": topic},
        },
        None,
        receive,
        send,
    )
