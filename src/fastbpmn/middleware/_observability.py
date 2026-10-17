import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPIReceiveEvent,
    AETPISendCallable,
    AETPISendEvent,
    ExternalTaskScope,
)

logger = logging.getLogger(__name__)

TERMINAL_EVENTS = {
    "externaltask.execute.complete": "completed",
    "externaltask.execute.failure": "failure",
    "externaltask.execute.error": "business_error",
    "externaltask.execute.abort": "aborted",
}
OPERATION_REQUESTS = {
    "externaltask.signal.emit": "signal",
    "externaltask.message.correlate": "message_correlation",
    "externaltask.variable.fetch": "variable_fetch",
}
OPERATION_RESPONSES = {
    "externaltask.signal.emitted": ("signal", True),
    "externaltask.signal.error": ("signal", False),
    "externaltask.message.delivered": ("message_correlation", True),
    "externaltask.message.error": ("message_correlation", False),
    "externaltask.variable.fetch.completed": ("variable_fetch", True),
    "externaltask.variable.fetch.failed": ("variable_fetch", False),
}


def task_attributes(
    scope: ExternalTaskScope,
    include_tenant: bool,
) -> dict[str, str]:
    task: Any = scope.get("task", {})
    attributes: dict[str, str] = {}
    for key, attribute in (
        ("topic_name", "fastbpmn.topic"),
        ("process_definition_key", "fastbpmn.process_definition_key"),
    ):
        value = task.get(key)
        if value is not None:
            attributes[attribute] = str(value)
    if include_tenant and task.get("tenant_id") is not None:
        attributes["fastbpmn.tenant_id"] = str(task["tenant_id"])
    return attributes


class EventLifecycleMiddleware(ABC):
    """Dispatch protocol lifecycle events to a telemetry implementation."""

    def __init__(self, app: AETPIApplication, *, include_tenant: bool = False) -> None:
        self.app = app
        self.include_tenant = include_tenant

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        if scope["type"] != "externaltask":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        attributes = task_attributes(scope, self.include_tenant)
        state = self.create_state(attributes)

        async def wrapped_receive() -> AETPIReceiveEvent:
            event = await receive()
            self.receive_event(state, event)
            return event

        async def wrapped_send(event: AETPISendEvent) -> None:
            self.send_event(state, event)
            await send(event)

        try:
            await self.app(scope, wrapped_receive, wrapped_send)
        except BaseException as exc:
            self.handle_exception(state, exc)
            raise
        finally:
            self.finish_state(state)

    @abstractmethod
    def create_state(self, attributes: dict[str, str]) -> Any:
        raise NotImplementedError

    def receive_event(self, state: Any, event: Mapping[str, Any]) -> None:
        del state, event

    def send_event(self, state: Any, event: Mapping[str, Any]) -> None:
        del state, event

    def handle_exception(self, state: Any, exc: BaseException) -> None:
        del state, exc

    def finish_state(self, state: Any) -> None:
        del state

    @staticmethod
    def record(method: Any, *args: Any) -> None:
        try:
            method(*args)
        except Exception:
            logger.debug("OpenTelemetry operation failed", exc_info=True)


def event_type(event: Mapping[str, Any]) -> str:
    return str(event.get("type"))
