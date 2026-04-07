import asyncio
from asyncio import Queue
from functools import reduce
from typing import TYPE_CHECKING

import structlog
from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveEvent,
    AETPISendEvent,
    ExternalTaskEndEvent,
    ExternalTaskExecuteAbortEvent,
    ExternalTaskExecuteAcceptEvent,
    ExternalTaskExecuteBusinessErrorEvent,
    ExternalTaskExecuteCompleteEvent,
    ExternalTaskExecuteFailureEvent,
    ExternalTaskExecuteRejectEvent,
    ExternalTaskExecuteRequestEvent,
    ExternalTaskExecuteStartEvent,
    ExternalTaskExtendLockEvent,
    ExternalTaskLockAcceptEvent,
    ExternalTaskScope,
    TaskScope,
)
from structlog.contextvars import bound_contextvars

from fastbpmn.aetpi import utils
from fastbpmn.camunda import ProcessEngine

if TYPE_CHECKING:
    pass


logger = structlog.get_logger(__name__)


class Camunda7ServerWorker:
    def __init__(
        self,
        *,
        process_engine: ProcessEngine,
        app: AETPIApplication,
    ):
        self.process_engine = process_engine
        self.app = app

    async def _lock_task(
        self, worker_id: str, task_id: str, lock_duration: int
    ) -> bool:
        # TDOO: proper exception handling?
        return await self.process_engine.external_task_lock(
            worker_id=worker_id, task_id=task_id, duration=lock_duration
        )

    async def _extend_lock_task(
        self, worker_id: str, task_id: str, lock_duration: int
    ) -> bool:
        # TDOO: proper exception handling?
        return await self.process_engine.external_task_extend_lock(
            worker_id=worker_id, task_id=task_id, duration=lock_duration
        )

    async def _fetch_variables(
        self,
        process_instance_id: str,
        execution_id: str,
    ) -> dict | bool:
        # TDOO: proper exception handling?
        # We think that might happen if someone kills the instance while trying to fetch
        # That means we should end the task
        # TODO: ensure to guard and parallelize this
        # TODO: sometimes the pe responds with status code 500

        execution_ids = await self.process_engine.process_instance_execution_ids(
            process_instance_id=process_instance_id,
            execution_id=execution_id,
        )

        result_futures = []

        async with asyncio.TaskGroup() as group:
            for execution_id in execution_ids:
                result_futures.append(
                    group.create_task(
                        self.process_engine.external_task_fetch_execution(
                            execution_id=execution_id,
                        )
                    )
                )

        results = list(map(lambda x: x.result(), result_futures))

        result = reduce(lambda x, y: x | y, results, {})

        return result

    async def _task_complete(
        self,
        worker_id: str,
        task_id: str,
        variables: dict | None,
    ) -> bool:
        # TDOO: proper exception handling?
        return await self.process_engine.external_task_complete(
            task_id=task_id, worker_id=worker_id, variables=variables or {}
        )

    async def _task_failure(
        self,
        worker_id: str,
        task_id: str,
        error_message: str | None,
        error_details: str | None,
        retries: int | None,
        retry_timeout: int | None,
        variables: dict | None,
        local_variables: dict | None,
    ) -> bool:
        # TDOO: proper exception handling?
        return await self.process_engine.external_task_failure(
            task_id=task_id,
            worker_id=worker_id,
            error_message=error_message,
            error_details=error_details,
            retries=retries,
            retry_timeout=retry_timeout,
            variables=variables or {},
            local_variables=local_variables or {},
        )

    async def _task_error(
        self,
        worker_id: str,
        task_id: str,
        error_code: str | None,
        error_message: str | None,
        variables: dict | None,
    ) -> bool:
        # TDOO: proper exception handling?
        return await self.process_engine.external_task_error(
            task_id=task_id,
            worker_id=worker_id,
            error_code=error_code,
            error_message=error_message,
            variables=variables or {},
        )

    async def _handle_lock_accepted(
        self, scope: TaskScope, event: ExternalTaskLockAcceptEvent
    ) -> ExternalTaskExecuteRequestEvent | ExternalTaskEndEvent:
        """
        Lock the task
        """
        # Try to lock the task at pe
        locked = await self._lock_task(
            worker_id=scope["worker_id"],
            task_id=scope["id"],
            lock_duration=event.get("lock_duration"),
        )

        if not locked:
            logger.debug("unable to lock external task")
            return utils.create_event_end()

        return utils.create_event_execute_request()

    async def _handle_lock_extend(
        self, scope: TaskScope, event: ExternalTaskExtendLockEvent
    ):

        extended = await self._extend_lock_task(
            worker_id=scope["worker_id"],
            task_id=scope["id"],
            lock_duration=event.get("lock_duration"),
        )
        if not extended:
            logger.debug("unable to extend lock for external task")

        logger.debug(
            "extended lock for external task", lock_duration=event.get("lock_duration")
        )

    async def _handle_execute_accept(
        self, scope: TaskScope, event: ExternalTaskExecuteAcceptEvent
    ) -> ExternalTaskExecuteStartEvent | ExternalTaskEndEvent:
        """
        Lock the task
        """
        requested_vars = event.get("required_variables")

        logger.debug(
            "request variables<%s>",
            "ALL"
            if requested_vars is None
            else ",".join(requested_vars)
            if requested_vars != set()
            else "None",
        )

        # Fetch the variables
        # TODO: we have no proper error handling here right now
        variables = await self._fetch_variables(
            process_instance_id=scope["process_instance_id"],
            execution_id=scope["execution_id"],
        )

        if variables is False:
            logger.error(
                "[server](receive) Fetch variables failed", extra={"scope": scope}
            )
            return utils.create_event_end()

        logger.debug(
            "fetched variables<%s>",
            ",".join(list(variables.keys())),
        )

        # Check if the required variables are present
        if requested_vars is None:
            return utils.create_event_execute_start(variables)

        missing_vars = requested_vars - set(variables.keys())
        if missing_vars:
            logger.debug(
                "some variables missing<%s>",
                missing_vars,
            )

        relevant_vars = {k: v for k, v in variables.items() if k in requested_vars}

        return utils.create_event_execute_start(relevant_vars)

    @staticmethod
    def _handle_execute_rejected(
        scope: TaskScope, _event: ExternalTaskExecuteRejectEvent
    ) -> ExternalTaskEndEvent:
        """
        Handles the rejection of the execution
        """
        logger.debug(
            "execution rejected, we might consider implementing task unlock here"
        )
        return utils.create_event_end()

    async def _handle_execute_complete(
        self, scope: TaskScope, event: ExternalTaskExecuteCompleteEvent
    ) -> ExternalTaskEndEvent:
        """
        Handles the completion of the execution
        """
        # Complete the task
        completed = await self._task_complete(
            worker_id=scope["worker_id"],
            task_id=scope["id"],
            variables=event.get("variables", None),
        )

        if not completed:
            logger.warning("unable to mark external task as completed")

        return utils.create_event_end()

    async def _handle_execute_failure(
        self, scope: TaskScope, event: ExternalTaskExecuteFailureEvent
    ) -> ExternalTaskEndEvent:
        """
        Handles the completion of the execution
        """
        # Complete the task
        completed = await self._task_failure(
            worker_id=scope["worker_id"],
            task_id=scope["id"],
            error_message=event.get("error_message", None),
            error_details=event.get("error_details", None),
            retries=event.get("retries", None),
            retry_timeout=event.get("retry_timeout", None),
            variables=event.get("variables", None),
            local_variables=event.get("local_variables", None),
        )

        if not completed:
            logger.warning("unable to mark external task as failed")

        return utils.create_event_end()

    async def _handle_execute_business_error(
        self, scope: TaskScope, event: ExternalTaskExecuteBusinessErrorEvent
    ) -> ExternalTaskEndEvent:
        """
        Handles the completion of the execution
        """
        # Complete the task
        completed = await self._task_error(
            worker_id=scope["worker_id"],
            task_id=scope["id"],
            error_code=event.get("error_code", None),
            error_message=event.get("error_message", None),
            variables=event.get("variables", None),
        )

        if not completed:
            logger.warning("unable to mark external task completed with business error")

        return utils.create_event_end()

    @staticmethod
    def _handle_execute_abort(
        scope: TaskScope, _event: ExternalTaskExecuteAbortEvent
    ) -> ExternalTaskEndEvent:
        """
        Handles the completion of the execution
        """
        return utils.create_event_end()

    async def handle_event(
        self,
        send_queue: Queue[AETPIReceiveEvent],
        task_scope: TaskScope,
        event: AETPISendEvent,
        prev_event: AETPISendEvent | None,
    ):
        """
        Handle the event received from the application
        """
        answer = None

        with bound_contextvars(curr_event=event, prev_event=prev_event):
            logger.debug("received %s event", event["type"])

            match event, prev_event:
                # Initial events: lock accept/reject
                case {"type": "externaltask.lock.accept"}, None:
                    answer = await self._handle_lock_accepted(task_scope, event)
                case {"type": "externaltask.lock.reject"}, None:
                    answer = utils.create_event_end()

                # After the lock is accepted:
                # - execute.accept: start the execution
                # - execute.reject: end the execution (rare case usually not required)
                case {"type": "externaltask.execute.accept"}, {
                    "type": "externaltask.lock.accept"
                }:
                    answer = await self._handle_execute_accept(task_scope, event)

                case {"type": "externaltask.execute.reject"}, {
                    "type": "externaltask.lock.accept"
                }:
                    # Should we unlock? or just end the task?
                    answer = self._handle_execute_rejected(task_scope, event)
                # After the execution is started there are a few possible outcomes:
                # - execute.complete: the task is completed
                # - execute.failure: the task failed
                # - execute.error: the task failed with a business error
                # - execute.abort: the task is aborted
                case {"type": "externaltask.execute.complete"}, {}:
                    answer = await self._handle_execute_complete(task_scope, event)

                case {"type": "externaltask.execute.failure"}, {}:
                    answer = await self._handle_execute_failure(task_scope, event)

                case {"type": "externaltask.execute.error"}, {}:
                    answer = await self._handle_execute_business_error(
                        task_scope, event
                    )

                case {"type": "externaltask.execute.abort"}, {}:
                    answer = utils.create_event_end()
                case {"type": "externaltask.execute.extendlock"}, {}:
                    await self._handle_lock_extend(task_scope, event)
                case _:
                    logger.warning(
                        "event unexpected while processing, remains unhandled"
                    )
                    raise ValueError("unexpected event")

        if answer is not None:
            logger.debug("Sending event %s", answer["type"])
            await send_queue.put(answer)
            logger.debug("Sended event %s", answer["type"])

    async def _task_file_variable(self, scope: TaskScope, variable_name: str) -> bytes:
        """
        Retrieve a file variable from the task
        """
        result, contents = await self.process_engine.external_task_file_variable(
            process_instance_id=scope["process_instance_id"],
            variable_name=variable_name,
        )

        return contents

    async def __call__(
        self, scope: ExternalTaskScope
    ) -> None:  # , mark_as_processed: callable):
        """
        Process the external task
        """
        send_queue: Queue[AETPIReceiveEvent] = Queue()

        task_scope = scope["task"]

        prev_event = None
        stopped = False

        async def sender() -> AETPIReceiveEvent:
            nonlocal stopped

            event_to_send = await send_queue.get()

            match event_to_send:
                case {"type": "externaltask.end"}:
                    stopped = True

            return event_to_send

        async def receiver(event: AETPISendEvent) -> None:
            nonlocal prev_event

            await self.handle_event(send_queue, task_scope, event, prev_event)
            # TODO: maybe this is a bit over optimistic
            # mark_as_processed()

            prev_event = event

        async def download_file_var(var_name: str) -> bytes:
            return await self._task_file_variable(task_scope, var_name)

        async def upload_file_var(var_name: str) -> bytes:
            raise NotImplementedError

        scope["x_download_file_var"] = download_file_var
        scope["x_upload_file_var"] = upload_file_var

        # First indicate the start of an arbitrary external task
        await send_queue.put(utils.create_event_start())
        await send_queue.put(utils.create_event_lock_request())

        # TODO : fix context (remove task dependency and add a method that can be used
        #        to retrieve a file var)
        # Todo: In the end we have to ensure that exceptions received are some how handled
        #       to failure tasks e.g.
        try:
            await self.app(scope, sender, receiver)
        except asyncio.CancelledError:
            logger.info(
                "[woker(%s)] we got the cancellation within the worker :( :( ",
                task_scope["worker_id"],
            )
