import logging

from aetpiref.typing import ExternalTaskScope

from yio_minions.errors import (
    FatalExternalTaskError,
    RetryExternalTask,
    TaskBusinessError,
)
from yio_minions.result import (
    AbortResult,
    BusinessErrorResult,
    ExternalTaskResult,
    FailureResult,
    FatalFailureResult,
    RetryOnFailureResult,
)
from yio_minions.task import Task

logger = logging.getLogger(__name__)


async def abort_external_task_handler(
    scope: ExternalTaskScope, exc: Exception
) -> ExternalTaskResult:

    task = Task(**scope["task"])

    error_message = str(exc) or type(exc).__qualname__

    logger.error(
        "[execute] <%s/%s (%s)> Abort requested (Reason: %s).",
        task.process_definition_key,
        task.topic_name,
        task.business_key,
        error_message,
        exc_info=exc,
    )
    return AbortResult()


async def retry_external_task_handler(
    scope: ExternalTaskScope, exc: RetryExternalTask
) -> ExternalTaskResult:

    task = Task(**scope["task"])

    retries = exc.retries or ((task.retries or 3) - 1)
    timeout = exc.retry_timeout or task.retry_timeout

    error_message = str(exc) or type(exc).__qualname__
    error_details = exc.detailed_message

    logger.exception(
        "[execute] <%s/%s (%s)> Error occurred (Retries: %d, Timeout: %d, Reason: %s).",
        task.process_definition_key,
        task.topic_name,
        task.business_key,
        retries,
        timeout,
        error_message,
        exc_info=exc,
    )

    return RetryOnFailureResult(
        error_message=str(exc),
        error_details=error_details,
        retries=retries,
        retry_timeout=timeout,
    )


async def fatal_external_task_error_handler(
    scope: ExternalTaskScope, exc: FatalExternalTaskError
) -> ExternalTaskResult:

    task = Task(**scope["task"])

    error_message = str(exc) or type(exc).__qualname__
    error_details = exc.detailed_message

    logger.exception(
        "[execute] <%s/%s (%s)> Error occurred (Reason: %s).",
        task.process_definition_key,
        task.topic_name,
        task.business_key,
        error_message,
        exc_info=exc,
    )
    return FatalFailureResult(
        error_message=error_message,
        error_details=error_details,
    )


async def business_external_task_error_handler(
    scope: ExternalTaskScope, exc: TaskBusinessError
) -> ExternalTaskResult:

    _task = Task(**scope["task"])
    error_message = str(exc) or type(exc).__qualname__

    return BusinessErrorResult(
        error_code=exc.error_code, error_message=error_message, variables=exc.variables
    )


async def uncaught_external_task_error_handler(
    scope: ExternalTaskScope, exc: Exception
) -> ExternalTaskResult:

    task = Task(**scope["task"])

    error_message = str(exc) or type(exc).__qualname__
    error_details = str(exc) or type(exc).__qualname__

    logger.exception(
        "[execute] <%s/%s (%s)> Uncaught Error occurred (Reason: %s).",
        task.process_definition_key,
        task.topic_name,
        task.business_key,
        error_message,
        exc_info=exc,
    )
    return FatalFailureResult(
        error_message=error_message,
        error_details=error_details,
    )


async def any_other_error_handler(
    scope: ExternalTaskScope, exc: Exception
) -> ExternalTaskResult:

    task = Task(**scope["task"])

    retries = (task.retries or 3) - 1
    timeout = task.retry_timeout

    error_message = str(exc) or type(exc).__qualname__
    error_details = str(exc) or type(exc).__qualname__

    logger.exception(
        "[execute] <%s/%s (%s)> Uncaught Error in backend occurred (Reason: %s).",
        task.process_definition_key,
        task.topic_name,
        task.business_key,
        error_message,
        exc_info=exc,
    )
    return FailureResult(
        error_message="APPLICATION / OPERATION ERROR",
        error_details=f"""
An uncaught error occurred in the application occurred

*) this is most likely caused by errors in the application and not caused within the external tasks itself
*) you migth not be able to resolve this error yourself, please contact your minion operator

Message: {error_message}

Details:
{error_details}

""",
        retries=retries,
        retry_timeout=timeout,
    )
