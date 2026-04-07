import logging

from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPIReceiveEvent,
    AETPISendCallable,
    ExternalTaskScope,
)

from yio_minions.aetpi import utils as eu
from yio_minions.utils.concurrency import run_in_threadpool
from yio_minions.utils.inspect import is_async_callable

from .types import GuardHandler

logger = logging.getLogger(__name__)


def handler_as_coroutine(handler: GuardHandler) -> GuardHandler:
    if is_async_callable(handler):
        return handler

    async def wrapped_handler(scope: ExternalTaskScope) -> bool:
        return await run_in_threadpool(handler, scope)

    return wrapped_handler


def wrap_app_with_guard(
    app: AETPIApplication,
    handler: GuardHandler | None,
) -> AETPIApplication:

    if handler is None:
        logger.warning(
            "No guard handler provided - Guard ineffective (not blocking anything)"
        )
        return app

    handler = handler_as_coroutine(handler)

    async def wrapped_app(
        scope: ExternalTaskScope, receive: AETPIReceiveCallable, send: AETPISendCallable
    ) -> None:

        task_scope = scope["task"]

        async def receiver() -> AETPIReceiveEvent:

            event = await receive()

            match event:
                case {"type": "externaltask.lock.request"}:
                    # in case of a lock request we check whether to answer with reject
                    if not await handler(scope):
                        message = f"""process<{task_scope.get("process_definition_key")}>/topic<{task_scope.get("topic_name")}> aborted / blocked"""

                        await send(
                            eu.create_event_lock_reject(
                                reason_code="CUSTOM", reason_message=message
                            )
                        )
                        return await receive()
            return event

        await app(scope, receiver, send)

    return wrapped_app
