import copy
import logging
from typing import Any, List, Optional, Tuple

import httpx
from aetpiref.typing import TaskScope
from pydantic import HttpUrl, TypeAdapter
from pydantic.alias_generators import to_snake
from structlog import getLogger
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random,
)

from fastbpmn.utils.asyncio import semaphore

from .asynchttp import AsyncCamundaHTTP
from .errors import (
    DeadlockSituationOccurredError,
    OptimisticLockError,
    RetryableError,
)
from .models import ExternalTask

logger = getLogger(__name__)
task_scope_adapter = TypeAdapter(list[ExternalTask])


def raise_known(exc: httpx.HTTPStatusError):

    if exc.response.status_code == 500:
        response_json = exc.response.json()

        match response_json:
            case {"code": 1}:
                raise OptimisticLockError() from exc
            # other than documented the code is not included in some responses
            case {"type": "OptimisticLockingException"}:
                raise OptimisticLockError() from exc
            case {"code": 10_000}:
                raise DeadlockSituationOccurredError() from exc


class ProcessEngine:
    """
    Basic Helper Functions
    """

    # number of tasks to fetch !
    BATCH_SIZE = 10

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        process_key: str = None,
        tenant_ids: Optional[Tuple[str, ...]] = None,
        camunda_base_url: HttpUrl | str = None,
        camunda_username: Optional[str] = None,
        camunda_password: Optional[str] = None,
        timeout: float | None = None,
        batch_size: int = BATCH_SIZE,
    ):
        """
        Setup access to Camunda Process Engine

        :param process_key: restrict on process id (camunda: processDefinitionKey)
        :param tenant_ids: restrict on process tenant_ids (camunda: tenantIdIn)
        :param camunda_base_url: Camunda REST API base_url
        :param camunda_username: Camunda REST API username
        :param camunda_password: Camunda REST API password
        """

        self.request = AsyncCamundaHTTP(
            base_url=camunda_base_url,
            username=camunda_username,
            password=camunda_password,
            timeout=timeout,
        )

        self._tenant_ids = tenant_ids
        self._tenant_id = tenant_ids[0] if tenant_ids else None
        self._process_key = process_key
        self.process_definition_id = None
        self._count = 0
        self._batch_size = batch_size

    @property
    def tenant_ids(self):
        """List of tenant_ids"""
        return self._tenant_ids

    @semaphore(n=5)
    async def process_instance_properties(
        self, process_instance_id: str
    ) -> dict | None:
        """
        Check (history) status for given process instance
        :return:
        """
        camunda_values = await self.request.get(
            f"/history/process-instance/{process_instance_id}"
        )

        return {to_snake(k): v for k, v in camunda_values.items()}

    async def process_instance_execution_ids(
        self, process_instance_id: str, execution_id: str
    ) -> list[str]:

        def recursive_execution_ids(
            tree: dict, execution_ids: list[str] = None
        ) -> dict[str, list[str]]:

            leaf_execution_ids = tree.get("executionIds", [])
            internal_execution_ids = (execution_ids or []) + leaf_execution_ids

            children = tree.get("childActivityInstances", [])

            if not children:
                return {
                    leaf_execution_ids[0]: copy.copy(internal_execution_ids),
                }

            result = {}

            for child in tree.get("childActivityInstances", []):
                result = result | recursive_execution_ids(
                    child, copy.copy(internal_execution_ids)
                )

            return result

        try:
            activity_instances = await self.request.get_raw(
                f"/process-instance/{process_instance_id}/activity-instances"
            )

            execution_id_hierarchy = recursive_execution_ids(activity_instances, [])

            return execution_id_hierarchy.get(execution_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (500,):
                raise RetryableError("Unable to retrieve execution ids")
            raise exc

    @semaphore(n=5)
    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_random(0, 1),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
    )
    async def external_task_fetch_execution(self, execution_id: str) -> dict | bool:
        """
        Try to get a lock for the external task specified by its id

        :params process_instance_id: the id of the external task
        :params worker_id: the id of the worker that wants to lock the task
        :params duration: (optional) the duration in milliseconds for which the lock should be valid
        """
        params = {"deserializeValues": False}
        try:
            return await self.request.get_raw(
                f"/execution/{execution_id}/localVariables", params=params
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (500,):
                raise RetryableError(
                    f"Unable to retrieve variables for execution id {execution_id}"
                )
            raise exc

    async def external_task_fetch(self, task_id: str) -> dict | bool:
        """
        Try to get a lock for the external task specified by its id

        :params process_instance_id: the id of the external task
        :params worker_id: the id of the worker that wants to lock the task
        :params duration: (optional) the duration in milliseconds for which the lock should be valid
        """
        params = {"deserializeValues": False}
        try:
            return await self.request.get_raw(
                f"/task/{task_id}/variables", params=params
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (500,):
                return False
            raise exc

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_random(0, 1),
        retry_error_callback=lambda _: False,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
    )
    @semaphore(1)
    async def external_task_lock(
        self, task_id: str, worker_id: str, duration: int | None = None
    ) -> bool:
        """
        Try to get a lock for the external task specified by its id

        :params task_id: the id of the external task
        :params worker_id: the id of the worker that wants to lock the task
        :params duration: (optional) the duration in milliseconds for which the lock should be valid
        """
        params = {
            "workerId": worker_id,
        }
        if duration:
            params.update(lockDuration=duration)

        try:
            await self.request.post_raw(f"/external-task/{task_id}/lock", data=params)
        except httpx.TimeoutException:
            return False
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return False
            raise_known(exc)
            raise exc

        return True

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_random(0, 1),
        retry_error_callback=lambda _: False,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
    )
    async def external_task_extend_lock(
        self, task_id: str, worker_id: str, duration: int
    ) -> bool:
        """
        Try to get a lock for the external task specified by its id

        :params task_id: the id of the external task
        :params worker_id: the id of the worker that wants to lock the task
        :params duration: (optional) the duration in milliseconds for which the lock should be valid
        """
        params = {
            "workerId": worker_id,
            "newDuration": duration,
        }

        try:
            await self.request.post_raw(
                f"/external-task/{task_id}/extendLock", data=params
            )
        except httpx.TimeoutException:
            return False
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return False
            raise_known(exc)
            raise exc

        return True

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_random(0, 1),
        retry_error_callback=lambda _: False,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
    )
    async def external_task_complete(
        self, task_id: str, worker_id: str, variables: dict
    ) -> bool:
        """
        Complete the external task specified by its id

        :params task_id: the id of the external task
        :params worker_id: the id of the worker that wants to complete the task
        :params variables: the variables to be set
        """
        params: dict[str, Any] = {
            "workerId": worker_id,
        }
        if variables:
            params["variables"] = variables

        try:
            await self.request.post_raw(
                f"/external-task/{task_id}/complete", data=params
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return False

            raise_known(exc)

            raise exc

        return True

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_random(0, 1),
        retry_error_callback=lambda _: False,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
    )
    async def external_task_failure(
        self,
        task_id: str,
        worker_id: str,
        error_message: str | None,
        error_details: str | None,
        retries: int | None,
        retry_timeout: int | None,
        variables: dict | None,
        local_variables: dict | None,
    ) -> bool:
        """
        Complete the external task specified by its id

        :params task_id: the id of the external task
        :params worker_id: the id of the worker that wants to complete the task
        :params variables: the variables to be set
        """
        params = {
            "workerId": worker_id,
        }

        if error_message:
            params.update(errorMessage=error_message)
        if error_details:
            params.update(errorDetails=error_details)
        if retries:
            params.update(retries=retries)
        if retry_timeout:
            params.update(retryTimeout=retry_timeout)
        if variables:
            params.update(variables=variables)
        if local_variables:
            params.update(localVariables=local_variables)

        try:
            await self.request.post_raw(
                f"/external-task/{task_id}/failure", data=params
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return False

            raise_known(exc)

            raise exc

        return True

    @retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_random(0, 1),
        retry_error_callback=lambda _: False,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
    )
    async def external_task_error(
        self,
        task_id: str,
        worker_id: str,
        error_code: str | None,
        error_message: str | None,
        variables: dict | None,
    ) -> bool:
        """
        Complete the external task specified by its id

        :params task_id: the id of the external task
        :params worker_id: the id of the worker that wants to complete the task
        :params variables: the variables to be set
        """
        params = {
            "workerId": worker_id,
        }

        if error_code:
            params.update(errorCode=error_code)
        if error_message:
            params.update(errorMessage=error_message)
        if variables:
            params.update(variables=variables)

        try:
            await self.request.post_raw(
                f"/external-task/{task_id}/bpmnError", data=params
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return False

            raise_known(exc)

            raise exc

        return True

    async def external_task_file_variable(
        self,
        process_instance_id: str,
        variable_name: str,
    ) -> tuple[bool, bytes | None]:
        """
        Get the file content of a variable

        :params process_instance_id: the id of the external task
        :params variable_name: the name of the variable
        """
        try:
            content = await self.request.get_raw(
                f"/process-instance/{process_instance_id}/variables/{variable_name}/data",
                binary=True,
            )
            return True, content
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return False, None
            raise exc

    async def get_pending_tasks(
        self,
    ) -> List[TaskScope]:
        """
        Get list of pending tasks by task/topic name.
        Filter on tenant_ids, process_keys and topics.

        :param list topics: topics to filter
        :param business_key_pattern: filter on business_key if given
        :param batch_size: maximum number of tasks to return ad once, default 10
        :param bool shuffle: randomize topics, default False

        :return: List of pending tasks
        """

        params = {
            "withRetriesLeft": 1,
            "notLocked": 1,
            "sorting": [
                {
                    "sortBy": "taskPriority",
                    "sortOrder": "desc",
                },
            ],
        }
        if self.tenant_ids:
            params.update(tenantIdIn=self.tenant_ids)

        res: list = await self.request.post("/external-task", data=params)
        if not res:
            return []

        snaked = task_scope_adapter.validate_python(res)

        dumped = task_scope_adapter.dump_python(snaked, by_alias=False)
        return dumped
