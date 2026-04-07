import logging
from typing import Any

from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPIReceiveEvent,
    AETPISendCallable,
    CapabilitiesScope,
    ExternalTaskScope,
    LifespanScope,
)

from yio_minions.errors import (
    AbortExternalTask,
    FatalExternalTaskError,
    RetryExternalTask,
    TaskBusinessError,
)
from yio_minions.utils.concurrency import run_in_threadpool
from yio_minions.utils.inspect import is_async_callable

from .handler import (
    abort_external_task_handler,
    any_other_error_handler,
    business_external_task_error_handler,
    fatal_external_task_error_handler,
    retry_external_task_handler,
    uncaught_external_task_error_handler,
)
from .types import ExceptionHandler, ExceptionHandlers
from .utils import wrap_app_handling_exceptions

logger = logging.getLogger(__name__)


__all__ = (
    "ExceptionHandler",
    "ExceptionHandlers",
    "ExceptionMiddleware",
    "ServerErrorMiddleware",
)


class ExceptionMiddleware:
    def __init__(
        self,
        app: AETPIApplication,
        handlers: Any,  # Mapping[Any, ExceptionHandler] | None = None,
    ) -> None:
        self.app = app
        self._uncaught_exception_handler = uncaught_external_task_error_handler
        self._exception_handlers: Any = {
            AbortExternalTask: abort_external_task_handler,
            FatalExternalTaskError: fatal_external_task_error_handler,
            RetryExternalTask: retry_external_task_handler,
            TaskBusinessError: business_external_task_error_handler,
        }  # ExceptionHandlers = {
        #    HTTPException: self.http_exception,
        #    WebSocketException: self.websocket_exception,
        # }
        if handlers is not None:  # pragma: no branch
            for key, value in handlers.items():
                self.add_exception_handler(key, value)

    def add_exception_handler(
        self,
        exc_class: type[Exception],
        handler: Any,  # ExceptionHandler,
    ) -> None:
        if issubclass(exc_class, Exception):
            self._exception_handlers[exc_class] = handler
        else:
            raise TypeError(f"Unsupported exception handler type: {exc_class}")

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        if scope["type"] != "externaltask":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        await wrap_app_handling_exceptions(
            self.app, self._exception_handlers, self._uncaught_exception_handler
        )(scope, receive, send)


class ServerErrorMiddleware:
    def __init__(self, app: AETPIApplication, *, handler: ExceptionHandler) -> None:
        self.app = app
        self.handler = handler or any_other_error_handler

    async def _handle_lifespan(
        self,
        scope: LifespanScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        return await self.app(scope, receive, send)

    async def _handle_capabilities(
        self,
        scope: CapabilitiesScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        return await self.app(scope, receive, send)

    async def _handle_external_task(
        self,
        scope: LifespanScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        """
        Handles the external task lifecycle, lets start by querying instant if we going to accept or reject
        """
        task_started = False
        handler = self.handler

        async def receiver() -> AETPIReceiveEvent:
            nonlocal task_started

            event = await receive()

            match event:
                # waiting for an event indicating that we have the lock and it might be worth creating an incident
                case {"type": "externaltask.execute.request"}:
                    # indication that the task_is_running
                    task_started = True
                case {"type": "externaltask.end"}:
                    task_started = False

            return event

        try:
            await self.app(scope, receiver, send)
        except Exception as exc:
            # Don't try to handle exceptions not occurred while handling a task
            logger.error(
                "[worker(%s)] unhandled exception when handling external task",
                scope["task"]["worker_id"],
                exc_info=exc,
                extra={"scope": scope},
            )

            if not task_started:
                raise

            if is_async_callable(handler):
                result = await handler(scope, exc)
            else:
                result = await run_in_threadpool(handler, scope, exc)
            if result is not None:
                await result(scope, receive, send)

            pass

    async def __call__(
        self,
        scope: ExternalTaskScope | CapabilitiesScope | LifespanScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:

        if scope["type"] == "capabilities":
            return await self._handle_capabilities(scope, receive, send)

        if scope["type"] == "lifespan":
            return await self._handle_lifespan(scope, receive, send)

        if scope["type"] == "externaltask":  # pragma: no cover
            return await self._handle_external_task(scope, receive, send)

        return await self.app(scope, receive, send)
