from typing import Any, Protocol, Type

import structlog
from aetpiref import typing as events
from aetpiref.typing import (
    AETPIReceiveCallable,
    AETPIScope,
    AETPISendCallable,
    ExternalTaskScope,
    TaskScope,
)

from fastbpmn.aetpi import utils as eu
from fastbpmn.context import Context
from fastbpmn.errors.process_engine import (
    InputDataValidationError,
    OutputDataValidationError,
)
from fastbpmn.models import InputModel, OutputModel
from fastbpmn.processor.routing import build_task_matcher
from fastbpmn.processor.task import HeartbeatHandler, TaskHandler, execute
from fastbpmn.result import ExternalTaskResult
from fastbpmn.task import Task, TaskProperties
from fastbpmn.utils.inspect import map_params

logger = structlog.getLogger(__name__)


class VariableDecoder(Protocol[InputModel]):
    async def __call__(
        self,
        context: Context,
        clazz: Type[InputModel] | None,
        variables: dict[str, Any],
    ) -> InputModel | None: ...


class VariableEncoder(Protocol[OutputModel]):
    async def __call__(
        self,
        output: OutputModel | None,
    ) -> dict[str, Any] | None: ...


async def default_decoder(
    _context: Context, clazz: Type[InputModel] | None, variables: dict[str, Any]
) -> InputModel | None:
    """
    Default decoder
    """
    if clazz is None:
        return None

    return clazz(**variables)


async def default_encoder(
    _context: Context, output: OutputModel | None
) -> dict[str, Any] | None:
    """
    Default encoder
    """
    if output is None:
        return None

    # TODO Maybe we should write a test to check how this works
    return output.model_dump(
        mode="python",
        by_alias=True,
        exclude_unset=False,
        exclude_none=True,  # Why? We should include defaults, as well as unset values but not None values?
    )


class ExternalTaskProcessor:
    """
    External Task Processor for Camunda 7
    """

    def __init__(
        self,
        task_properties: list[TaskProperties],
        *,
        variable_decoder: VariableDecoder | None = None,
        variable_encoder: VariableEncoder | None = None,
    ):
        self.task_properties = task_properties
        self.task_matcher = build_task_matcher(task_properties)
        self.variable_decoder = variable_decoder or default_decoder
        self.variable_encoder = variable_encoder or default_encoder

    @staticmethod
    async def _handle_lock_request(
        task_scope: TaskScope,
        task_properties: TaskProperties | None,
        _event: events.ExternalTaskLockRequestEvent,
        send: AETPISendCallable,
    ) -> None:
        """
        Handle the lock request
        """
        if task_properties is None:
            message = f"""process<{task_scope.get("process_definition_key")}>/topic<{task_scope.get("topic_name")}>"""

            await send(
                eu.create_event_lock_reject(
                    reason_code="NOT_IMPLEMENTED", reason_message=message
                )
            )
        else:
            await send(eu.create_event_lock_accept(task_properties.lock_duration))

    @staticmethod
    async def _handle_execute_request(
        task_properties: TaskProperties, send: AETPISendCallable
    ):
        """
        Let's figure out which variables we need for execution all or None ... more is to complicated
        """
        requires_vars = task_properties.input_class is not None

        if requires_vars:
            await send(eu.create_event_execute_accept(None))  # requests all variables
        else:
            await send(eu.create_event_execute_accept(set()))

    async def _decode_input(
        self,
        clazz: type[InputModel],
        context: Context,
        variables: dict[str, Any],
    ) -> InputModel | None:
        try:
            return await self.variable_decoder(context, clazz, variables)
        except ValueError as e:
            raise InputDataValidationError(
                str(e),
            ) from e

    async def _decode_output(
        self,
        clazz: type[OutputModel],
        context: Context,
        variables: dict[str, Any] | OutputModel | None,
    ) -> dict[str, Any] | None:
        # todo<dh>: consider using a type adapter, that might be capable to decode any kind of pydantic related
        #           data to dict[str, Any]
        try:
            return await self.variable_encoder(context, variables)
        except ValueError as e:
            raise OutputDataValidationError(
                str(e),
            ) from e

    async def _handle_execute_start_event(
        self,
        scope: ExternalTaskScope,
        task_properties: TaskProperties,
        event: events.ExternalTaskExecuteStartEvent,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ):
        """
        This method is actually the execution of the task.
        """
        task_scope: TaskScope = scope["task"]
        context: Context = scope["context"]

        handler = task_properties.handler
        input_data = await self._decode_input(
            task_properties.input_class, context, event["variables"]
        )
        # TODO: create task ... (we need a new implementation without pe dep)
        task = Task(**task_scope)

        params = map_params(handler, input_data, task, task_properties, context)

        handler = TaskHandler(handler, kwargs=params)
        heartbeat = HeartbeatHandler(scope, send)

        output = await execute(heartbeat, handler)

        # in case of direct response of a result, call the result
        if isinstance(output, ExternalTaskResult):
            return await output(scope, receive, send)

        # get a vars dict from output data
        vars_dict = await self._decode_output(
            task_properties.output_class, context, output
        )

        # send the result
        return await send(eu.create_event_execute_complete(vars_dict))

    async def _handle_capabilities_request_event(
        self,
        scope: AETPIScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        event = await receive()

        match event:
            case {"type": "capabilities.request"}:
                # build the capabilities and send them out
                capabilities = [
                    {
                        "topic_name": props.topic,
                        "process_definition_key": props.process_definition_key,
                    }
                    for props in self.task_properties
                ]
                await send(eu.create_capabilities_response_event(capabilities))
            case _:
                logger.warning(f"Unexpected event: {event}")
        return

    def update_task_scope(
        self, scope: TaskScope, task_properties: TaskProperties | None
    ) -> Task:
        """
        Update some fields within scope if unset
        """
        if task_properties is None:
            return Task(**scope)

        task_properties: TaskProperties

        scope["retries"] = scope.get("retries", task_properties.retries)
        scope["retry_timeout"] = scope.get(
            "retry_timeout", task_properties.retry_timeout
        )
        scope["lock_duration"] = scope.get(
            "lock_duration", task_properties.lock_duration
        )
        scope["title"] = scope.get("title", task_properties.title)
        scope["description"] = scope.get("description", task_properties.description)

        return Task(**scope)

    async def __call__(
        self,
        scope: AETPIScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        """
        Process the external task
        """
        if scope["type"] == "capabilities":
            return await self._handle_capabilities_request_event(scope, receive, send)

        # Check if the protocol is supported
        if scope["type"] != "externaltask":  # pragma: no cover
            return

        if scope.get("protocol") != "camunda7":
            raise TypeError(f"Unsupported protocol: {scope.get('protocol')}")
        # conditions met
        task_scope = scope.get("task")

        # we can immediately check if we have the possibility to handle that task
        # s.t. we can decide if we accept the lock request or not.
        task_properties = self.task_matcher(task_scope)
        # with matched task_properties we are able to update several variables
        self.update_task_scope(task_scope, task_properties)

        prev_event = None

        while True:
            event = await receive()
            # a more sophisticated implementation would use a state machine
            # and check if the event is valid in the current state
            # but for testing thats ok.
            match event, prev_event:
                case {"type": "externaltask.start"}, None:
                    pass
                # The lock request is the first event we receive after the start event
                case {"type": "externaltask.lock.request"}, {
                    "type": "externaltask.start"
                }:
                    await self._handle_lock_request(
                        task_scope, task_properties, event, send
                    )
                # execute request is allowed only after the lock request
                case {"type": "externaltask.execute.request"}, {
                    "type": "externaltask.lock.request"
                }:
                    await self._handle_execute_request(task_properties, send)
                case {"type": "externaltask.execute.start"}, {
                    "type": "externaltask.execute.request"
                }:
                    await self._handle_execute_start_event(
                        scope, task_properties, event, receive, send
                    )
                case {"type": "externaltask.end"}, _:  # any previous event is allowed
                    break
                case _:
                    logger.warning(f"Unexpected event: {event}")

            prev_event = event

        logger.debug(
            "Processing completed, exiting the event handling loop",
            extra={"scope": scope},
        )
