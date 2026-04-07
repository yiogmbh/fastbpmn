import asyncio
import functools
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

import structlog
from aetpiref.typing import AETPISendCallable, ExternalTaskScope

from fastbpmn.utils.concurrency import run_in_threadpool

__all__ = ["TaskHandler"]

logger = structlog.get_logger(__name__)
P = ParamSpec("P")
T = TypeVar("T")


class TaskHandler:
    def __init__(
        self, task: Callable[P, T], args: list | None = None, kwargs: dict | None = None
    ):
        self.task = task
        self.args = args or []
        self.kwargs = kwargs or {}

    async def __call__(self) -> T:

        if is_async_callable(self.task):
            output = await self.task(*self.args, **self.kwargs)
        else:
            output = await run_in_threadpool(self.task, **self.kwargs)

        return output


class HeartbeatHandler:
    def __init__(self, scope: ExternalTaskScope, send: AETPISendCallable):
        self.scope = scope
        self.send = send

    async def _extend_lock(self, lock_duration: int) -> None:

        return await self.send(
            {"type": "externaltask.execute.extendlock", "lock_duration": lock_duration}
        )

    async def __call__(self) -> None:
        lock_duration = self.scope["task"]["lock_duration"]

        try:
            while True:
                await asyncio.sleep(lock_duration / 2000)
                await self._extend_lock(lock_duration)
        except asyncio.CancelledError:
            logger.debug("heartbeat task has been cancelled / stopped")


async def execute(
    heartbeat: HeartbeatHandler,
    task: TaskHandler,
) -> Coroutine[Any, Any, T]:

    worker_task = asyncio.create_task(task(), name="worker_task")
    heartbeat_task = asyncio.create_task(heartbeat(), name="heartbeat_task")

    worker_task.add_done_callback(lambda _: heartbeat_task.cancel())

    await asyncio.wait([worker_task, heartbeat_task], return_when=asyncio.ALL_COMPLETED)

    return worker_task.result()


def is_async_callable(obj: Any) -> bool:
    while isinstance(obj, functools.partial):
        obj = obj.func

    return asyncio.iscoroutinefunction(obj) or (
        callable(obj) and asyncio.iscoroutinefunction(obj.__call__)
    )
