import asyncio
import re
from asyncio import Event
from asyncio.queues import Queue, QueueFull
from random import shuffle as shuffle_topics
from typing import Callable, Protocol

import structlog
from aetpiref.typing import Capability, ExternalTaskScope, TaskScope
from aiolimiter import AsyncLimiter
from culsans import QueueShutDown

from fastbpmn.aetpi.utils import create_externaltask_scope
from fastbpmn.camunda import ProcessEngine

logger = structlog.get_logger(__name__)


class PendingExternalTasks(Protocol):
    """
    A simple protocol that defines the interface for listing pending external tasks from any source.
    """

    async def __call__(self, limit: int) -> list[TaskScope]:
        """
        Get a list of pending tasks from the source.
        """
        pass


class TaskFetcher:
    def __init__(
        self,
        process_engine: ProcessEngine,
        capabilities: list[Capability],
        business_key_alike: re.Pattern | None = None,
        shuffle: bool = True,
    ):
        self.process_engine = process_engine
        self.capabilities = capabilities

        self.shuffle = shuffle
        self.business_key_pattern = (
            re.compile(business_key_alike) if business_key_alike else None
        )

        self.filter_predicate = self._build_filter_predicate()

    def _build_capability_predicate(self) -> Callable[[TaskScope], bool]:

        capabilities = set(
            (c.get("process_definition_key", None), c.get("topic_name", None))
            for c in self.capabilities
        )

        def match_capability(scope: TaskScope) -> bool:

            process_definition_key = scope["process_definition_key"]
            topic_name = scope["topic_name"]

            if (process_definition_key, topic_name) in capabilities:
                return True
            if (None, topic_name) in capabilities:
                return True

            return False

        return match_capability

    def _build_business_key_predicate(self) -> Callable[[TaskScope], bool]:

        if self.business_key_pattern is None:
            return lambda _: True

        def match_business_key(scope: TaskScope) -> bool:
            business_key = scope.get("business_key", None)

            return (
                business_key is not None
                and self.business_key_pattern.fullmatch(business_key) is not None
            )

        return match_business_key

    def _build_filter_predicate(self) -> Callable[[TaskScope], bool]:

        predicates = [
            self._build_capability_predicate(),
        ]

        if self.business_key_pattern is not None:
            predicates.append(self._build_business_key_predicate())

        return lambda scope: all((predicate(scope) for predicate in predicates))

    def with_capabilities(self, capabilities: list[Capability]) -> "TaskFetcher":
        self.capabilities = capabilities
        self.filter_predicate = self._build_filter_predicate()
        return self

    async def __call__(self, limit: int) -> list[TaskScope]:

        pending = await self.process_engine.get_pending_tasks()

        matching = list(filter(self.filter_predicate, pending))

        if self.shuffle:
            shuffle_topics(matching)

        return matching[:limit]


class SimpleExternalTaskProducer:
    """
    An simple producer that queries the given process engine for pending tasks and puts them into the queue
    whenever the queue is empty.
    """

    def __init__(
        self, shutdown: Event, fetcher: TaskFetcher, queue: Queue[ExternalTaskScope]
    ):
        self.shutdown = shutdown
        self.queue = queue
        self.queue_size = queue.maxsize
        self.fetcher = fetcher

    @staticmethod
    def create_for_fetcher(
        shutdown: Event,
        queue: Queue[ExternalTaskScope],
        process_engine: ProcessEngine,
        capabilities: list[Capability],
        business_key_alike: re.Pattern | None = None,
        shuffle: bool = True,
    ) -> "SimpleExternalTaskProducer":

        fetcher = TaskFetcher(process_engine, capabilities, business_key_alike, shuffle)

        return SimpleExternalTaskProducer(shutdown, fetcher, queue)

    def with_capabilities(
        self, capabilities: list[Capability]
    ) -> "SimpleExternalTaskProducer":
        self.fetcher = self.fetcher.with_capabilities(capabilities)
        return self

    async def _get_pending_tasks(self) -> list[TaskScope]:
        """
        Get the pending tasks from the fetcher
        """
        limit = self.queue_size
        logger.debug("get_pending_tasks: Fetching pending tasks <limit=%d>", limit)
        tasks = await self.fetcher(limit)
        logger.debug(
            "get_pending_tasks: Got %d pending tasks <%d/%d>",
            len(tasks),
            len(tasks),
            limit,
        )
        return tasks

    def _put_tasks_into_queue(self, tasks: list[TaskScope]) -> TaskScope | None:
        """
        Put the task into the queue
        """
        scopes = list(map(create_externaltask_scope, tasks))
        enqueued = []

        try:
            for scope in scopes:
                self.queue.put_nowait(scope)
                enqueued.append(scope)
        except QueueFull:
            # The queue is full, we can't put the task into the queue
            logger.debug(
                "queue_full: Skip %d/%d tasks because the queue is full at the moment",
                len(scopes) - len(enqueued),
                len(scopes),
                queue={
                    "size": self.queue_size,
                },
            )
        except QueueShutDown:
            logger.debug("queue_shutdown: going to exit soon")
        except Exception as e:
            logger.error("error when trying to put work into queue", exc_info=e)
            raise e from e

    async def __call__(self):

        limiter = AsyncLimiter(2, 1)

        try:
            while not self.shutdown.is_set():
                async with limiter:
                    # 1) Get the pending tasks
                    pending_tasks = await self._get_pending_tasks()
                    # 2) Put the pending tasks into the queue
                    self._put_tasks_into_queue(pending_tasks)

            logger.info("producer_stopped")
        except QueueShutDown:
            logger.debug("producer_stopped, queue was shut down")
        except asyncio.CancelledError:
            # We can do some cleanup here if needed
            raise
        except Exception as e:
            logger.error("producer_error: %s", e, exc_info=e)
            raise e
        finally:
            logger.debug("producer_stopped")
