from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import types
from asyncio import Queue
from typing import Any, Callable, Generator, Sequence, TypeVar

from aetpiref.typing import (
    AETPIApplication,
    LifespanScope,
    LifespanShutdownCompleteEvent,
    LifespanShutdownEvent,
    LifespanShutdownFailedEvent,
    LifespanStartupCompleteEvent,
    LifespanStartupEvent,
    LifespanStartupFailedEvent,
)

from yio_minions.aetpi.utils import create_lifespan_scope
from yio_minions.utils.inspect import is_async_callable

LifespanReceiveMessage = LifespanStartupEvent | LifespanShutdownEvent
LifespanSendMessage = (
    LifespanStartupFailedEvent
    | LifespanShutdownFailedEvent
    | LifespanStartupCompleteEvent
    | LifespanShutdownCompleteEvent
)

STATE_TRANSITION_ERROR = "Got invalid state transition on lifespan protocol."


class LifespanOn:
    def __init__(self, app: AETPIApplication) -> None:
        self.app = app
        self.logger = logging.getLogger("minion.error")
        self.startup_event = asyncio.Event()
        self.shutdown_event = asyncio.Event()
        self.receive_queue: Queue[LifespanReceiveMessage] = asyncio.Queue()
        self.error_occurred = False
        self.startup_failed = False
        self.shutdown_failed = False
        self.should_exit = False
        self.state: dict[str, Any] = {}

    async def startup(self) -> None:
        self.logger.info("Waiting for application startup.")

        loop = asyncio.get_event_loop()
        main_lifespan_task = loop.create_task(self.main())  # noqa: F841
        # Keep a hard reference to prevent garbage collection
        # See https://github.com/Kludex/uvicorn/pull/972
        startup_event: LifespanStartupEvent = {"type": "lifespan.startup"}
        await self.receive_queue.put(startup_event)
        await self.startup_event.wait()

        if self.startup_failed or self.error_occurred:
            self.logger.error("Application startup failed. Exiting.")
            self.should_exit = True
        else:
            self.logger.info("Application startup complete.")

    async def shutdown(self) -> None:
        if self.error_occurred:
            return
        self.logger.info("Waiting for application shutdown.")
        shutdown_event: LifespanShutdownEvent = {"type": "lifespan.shutdown"}
        await self.receive_queue.put(shutdown_event)
        await self.shutdown_event.wait()

        if self.shutdown_failed or self.error_occurred:
            self.logger.error("Application shutdown failed. Exiting.")
            self.should_exit = True
        else:
            self.logger.info("Application shutdown complete.")

    async def main(self) -> None:
        try:
            app = self.app
            scope: LifespanScope = create_lifespan_scope(self.state)
            await app(scope, self.receive, self.send)
        except BaseException:
            self.asgi = None
            self.error_occurred = True
            if self.startup_failed or self.shutdown_failed:
                return
        finally:
            self.startup_event.set()
            self.shutdown_event.set()

    async def send(self, message: LifespanSendMessage) -> None:
        assert message["type"] in (
            "lifespan.startup.complete",
            "lifespan.startup.failed",
            "lifespan.shutdown.complete",
            "lifespan.shutdown.failed",
        )

        if message["type"] == "lifespan.startup.complete":
            assert not self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.startup_event.set()

        elif message["type"] == "lifespan.startup.failed":
            assert not self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.startup_event.set()
            self.startup_failed = True
            if message.get("message"):
                self.logger.error(message["message"])

        elif message["type"] == "lifespan.shutdown.complete":
            assert self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.shutdown_event.set()

        elif message["type"] == "lifespan.shutdown.failed":
            assert self.startup_event.is_set(), STATE_TRANSITION_ERROR
            assert not self.shutdown_event.is_set(), STATE_TRANSITION_ERROR
            self.shutdown_event.set()
            self.shutdown_failed = True
            if message.get("message"):
                self.logger.error(message["message"])

    async def receive(self) -> LifespanReceiveMessage:
        return await self.receive_queue.get()


_T = TypeVar("_T")


class _AsyncLiftContextManager(contextlib.AbstractAsyncContextManager[_T]):
    def __init__(self, cm: contextlib.AbstractContextManager[_T]):
        self._cm = cm

    async def __aenter__(self) -> _T:
        return self._cm.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool | None:
        return self._cm.__exit__(exc_type, exc_value, traceback)


def _wrap_gen_lifespan_context(
    lifespan_context: Callable[[Any], Generator[Any, Any, Any]],
) -> Callable[[Any], contextlib.AbstractAsyncContextManager[Any]]:
    cmgr = contextlib.contextmanager(lifespan_context)

    @functools.wraps(cmgr)
    def wrapper(app: Any) -> _AsyncLiftContextManager[Any]:
        return _AsyncLiftContextManager(cmgr(app))

    return wrapper


class NoopLifespan:
    def __init__(self, app: AETPIApplication):
        self._app = app

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, *exc_info: object) -> None:
        pass

    def __call__(self: _T, app: object) -> _T:
        return self


class DeprecatedLifespan:
    def __init__(
        self,
        app: AETPIApplication,
        startup_handlers: Sequence[Callable[[], Any]] | None,
        shutdown_handlers: Sequence[Callable[[], Any]] | None,
    ):
        self._app = app

        self._startup_handlers = (
            [] if startup_handlers is None else list(startup_handlers)
        )
        self._shutdown_handlers = (
            [] if shutdown_handlers is None else list(shutdown_handlers)
        )

    async def __aenter__(self) -> None:
        for handler in self._startup_handlers:
            if is_async_callable(handler):
                await handler()
            else:
                handler()

    async def __aexit__(self, *exc_info: object) -> None:

        for handler in self._shutdown_handlers:
            if is_async_callable(handler):
                await handler()
            else:
                handler()

    def __call__(self: _T, app: object) -> _T:
        return self
