import asyncio
import copy
import hashlib
import re
import signal
from asyncio import CancelledError, Event, Queue, Semaphore, shield
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Generator

import structlog
from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveEvent,
    AETPISendEvent,
    Capability,
)
from pydantic import HttpUrl, validate_call
from structlog.contextvars import bound_contextvars

from yio_minions.aetpi import utils
from yio_minions.camunda import ProcessEngine
from yio_minions.lifespan import LifespanOn
from yio_minions.utils.asyncio import cancel_and_wait
from yio_minions.utils.func import call_once_only

from .middleware import Camunda7VariablePreprocessor
from .producer import SimpleExternalTaskProducer
from .queue import UniqueQueue
from .worker import Camunda7ServerWorker

logger = structlog.get_logger()


def worker_id_generator(name: str) -> Generator[str, None, None]:

    idx = 0
    while True:
        hash_name = f"{name}-{idx:08d}"
        hash_digest = hashlib.md5(hash_name.encode("utf-8")).hexdigest()
        next_name = f"{name}-{hash_digest[-8:]}"
        yield next_name
        idx += 1


def timeout_to_seconds(timeout: timedelta | float | None) -> float | None:
    """
    Convert a timeout to seconds
    """
    if timeout is None:
        return None
    if isinstance(timeout, timedelta):
        return timeout.total_seconds()
    return timeout


class CapabilityChecker:
    def __init__(self, app: AETPIApplication):
        self.app = app
        self.capabilities = []

    async def __call__(self) -> list[Capability]:
        send_queue: Queue[AETPIReceiveEvent] = Queue()

        scope = utils.create_capabilities_scope()

        async def sender() -> AETPIReceiveEvent:
            return await send_queue.get()

        async def receiver(event: AETPISendEvent) -> None:

            match event:
                case {"type": "capabilities.response"}:
                    self.capabilities = event["capabilities"]

        # First indicate the start of an arbitrary external task
        await send_queue.put(utils.create_capabilities_request_event())

        await self.app(scope, sender, receiver)

        return self.capabilities


class Camunda7Server:
    @validate_call
    def __init__(
        self,
        app: AETPIApplication,
        *,
        name: str,
        camunda_url: HttpUrl | str,
        parallelism: int = 10,
        shuffle_pending: bool = True,
        tenant_ids: list[str] | None = None,
        business_key_alike: re.Pattern | None = None,
        camunda_username: str | None = None,
        camunda_password: str | None = None,
        camunda_timeout: float | None = None,
    ):
        self.app = Camunda7VariablePreprocessor(app)
        self.lifespan = LifespanOn(self.app)
        self.capability = CapabilityChecker(self.app)

        self.process_engine = ProcessEngine(
            camunda_base_url=camunda_url,
            camunda_username=camunda_username,
            camunda_password=camunda_password,
            timeout=camunda_timeout,
            tenant_ids=tenant_ids,
        )

        self.name = name
        self.shutdown = Event()
        self.interrupts = 0

        self.parallelism = parallelism
        self.queue = UniqueQueue(parallelism).async_q

        self.handler = Camunda7ServerWorker(
            process_engine=self.process_engine, app=self.app
        )
        self.shuffle_pending = shuffle_pending

        # internal fields
        self.producer = SimpleExternalTaskProducer.create_for_fetcher(
            shutdown=self.shutdown,
            queue=self.queue,
            process_engine=self.process_engine,
            capabilities=[],
            business_key_alike=business_key_alike,
            shuffle=self.shuffle_pending,
        )

    @asynccontextmanager
    async def _producer(self):
        self.capabilities = await self.capability()

        yield self.producer.with_capabilities(self.capabilities)

    @asynccontextmanager
    async def _lifespan(self):
        await self.lifespan.startup()
        try:
            yield
        finally:
            await shield(self.lifespan.shutdown())

    @asynccontextmanager
    async def _tasks_set(self):
        pending = set()
        yield pending
        if len(pending) > 0:
            await asyncio.wait(pending)

    async def __call__(self):

        async with (
            self._lifespan() as _,
            self._producer() as producer,
            self._tasks_set() as tasks,
        ):
            try:
                producer_task = asyncio.create_task(producer(), name="producer")
                worker_task = asyncio.create_task(self.workers(), name="workers")
                # worker_tasks = map(
                #    lambda idx: asyncio.create_task(self.consume_and_process(), name=f"worker_{idx:02d}"),
                #    range(self.parallelism)
                # )
                # worker_waiter = asyncio.create_task(
                #    asyncio.wait([w for w in worker_tasks], return_when=asyncio.ALL_COMPLETED))

                # self.tasks.append(producer_task)
                # self.tasks.extend(worker_tasks)

                _, pending = await asyncio.wait(
                    [shield(producer_task), shield(worker_task)],
                    return_when=asyncio.ALL_COMPLETED,
                )
                for p in pending:
                    tasks.add(p)

            except CancelledError:
                logger.error(
                    "ayncio.exceptions.CancelledError occured, going to die ",
                    exc_info=True,
                )

    def run(self):
        signal.signal(signal.SIGINT, self.exit_handler)
        signal.signal(signal.SIGTERM, self.exit_handler)
        signal.signal(signal.SIGHUP, self.exit_handler)

        asyncio.run(self())

    def exit_handler(self, signum, *args) -> None:
        # pylint: disable=unused-argument
        self.interrupts += 1
        self.shutdown.set()
        self.queue.shutdown()

        # Todo: check if this works in any fashion (i have the feeling it don't)
        if self.interrupts > 1:
            logger.warning("Going to cancel all pending tasks")
            # for task in self.tasks:
            #    # task: asyncio.Task
            #    task.cancel()

        logger.warning(
            f"{self.name} is going to stop working, because of the "
            f"Signal {signal.Signals(signum).name}.\nAlready started tasks get finished!"
        )

    async def workers(self):
        """
        Try to create consumer in an infinite loop using Semaphore up to parallelism
        """
        next_worker_id = worker_id_generator(self.name)
        semaphore = Semaphore(self.parallelism)
        # shutdown_wait = asyncio.create_task(self.shutdown.wait())
        tasks = set()

        @asynccontextmanager
        async def wait_():

            shutdown_wait = asyncio.create_task(self.shutdown.wait())
            semaphore_acquire = asyncio.create_task(semaphore.acquire())

            done, pending = await asyncio.wait(
                {shutdown_wait, semaphore_acquire}, return_when=asyncio.FIRST_COMPLETED
            )
            if shutdown_wait in done:
                # Shutdown signal was set - cancel semaphore acquisition and break
                await cancel_and_wait(semaphore_acquire)
                yield None
            elif semaphore_acquire in done:
                # Semaphore was acquired - create new worker
                await cancel_and_wait(shutdown_wait)

                @call_once_only
                def _release(t: asyncio.Task):
                    semaphore.release()
                    logger.debug(
                        "[worker(%s)] released semaphore",
                        t.get_name(),
                        worker_id=t.get_name(),
                    )

                yield _release
            else:
                logger.warning(
                    "[worker(%s)] unreachable condition reached !!!",
                    t.get_name(),
                    worker_id=t.get_name(),
                )

        try:
            while not self.shutdown.is_set():
                async with wait_() as release:
                    if release is None:
                        break
                    name = next(next_worker_id)
                    t = asyncio.create_task(self.worker(name=name), name=name)
                    tasks.add(t)
                    t.add_done_callback(release)
                    t.add_done_callback(tasks.discard)
                    t.add_done_callback(lambda t: t.exception())

        finally:
            if len(tasks) > 0:
                wait_to_finish = asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
                await shield(wait_to_finish)

    async def worker(self, name: str):

        scope = await self.queue.get()
        if scope is None:
            return

        with bound_contextvars(
            scope=scope,
            worker_id=name,
        ):

            @call_once_only
            def mark_as_processed():
                self.queue.task_done()

            handler = self.handler

            scope = copy.copy(scope)
            scope["task"]["worker_id"] = name

            try:
                logger.debug(
                    "Worker[start] processing <%s/%s>",
                    scope["task"]["process_definition_key"],
                    scope["task"]["id"],
                )

                piece_of_work = asyncio.create_task(handler(scope))
                await shield(piece_of_work)  # , mark_as_processed)

                logger.debug(
                    "Worker[ended] processing <%s/%s>",
                    scope["task"]["process_definition_key"],
                    scope["task"]["id"],
                )
            finally:
                mark_as_processed()
