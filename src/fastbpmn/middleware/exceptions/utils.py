from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPIReceiveEvent,
    AETPISendCallable,
    ExternalTaskScope,
)

from fastbpmn.middleware.exceptions import ExceptionHandler, ExceptionHandlers
from fastbpmn.utils.concurrency import run_in_threadpool
from fastbpmn.utils.inspect import is_async_callable


def _lookup_exception_handler(
    exc_handlers: ExceptionHandlers, exc: Exception
) -> ExceptionHandler | None:
    for cls in type(exc).__mro__:
        if cls in exc_handlers:
            return exc_handlers[cls]
    return None


def wrap_app_handling_exceptions(
    app: AETPIApplication,
    exception_handlers: ExceptionHandlers,
    uncaught_exception_handler: ExceptionHandler,
) -> AETPIApplication:

    async def wrapped_app(
        scope: ExternalTaskScope, receive: AETPIReceiveCallable, send: AETPISendCallable
    ) -> None:
        task_started = False

        async def receiver() -> AETPIReceiveEvent:
            nonlocal task_started

            event = await receive()

            match event:
                case {"type": "externaltask.execute.start"}:
                    # indication that the task_is_running
                    task_started = True
                case {"type": "externaltask.end"}:
                    task_started = False

            return event

        try:
            await app(scope, receiver, send)
        except Exception as exc:
            if not task_started:
                # Don't try to handle exceptions not occurred while handling a task
                raise

            handler: ExceptionHandler | None = None

            if handler is None:
                # try to find a suitable exception handler
                handler = _lookup_exception_handler(exception_handlers, exc)

            if handler is None:
                # use a default handler to catch any other errors
                handler = uncaught_exception_handler

            # todo: add context back to exc handlers
            if is_async_callable(handler):
                result = await handler(scope, exc)
            else:
                result = await run_in_threadpool(handler, scope, exc)
            if result is not None:
                await result(scope, receive, send)

    return wrapped_app
