import logging
from typing import Any, Literal

import aetpiref.typing as types

logger = logging.getLogger(__name__)


def verify_external_task_scope(scope: types.ExternalTaskScope) -> None:
    """
    Verify the scope type to ensure the scope issued belongs to external task processing.
    """
    if scope.get("type", None) != "externaltask":
        raise TypeError(f"Unsupported scope type: {scope.get('type')}")

    if scope.get("protocol", None) != "camunda7":
        logger.warning(
            f"ExternalTaskScope protocol is not yet used: protocol<{scope.get('protocol')}>"
        )

    return None


def receive_event_type(event: types.AETPIReceiveEvent) -> str:
    """
    Extracts the event type from the event.
    """
    return str(event.get("type"))


def create_event_start() -> types.ExternalTaskStartEvent:
    """
    Create an event to indicate the beginning of an external task processing.
    """
    return {"type": "externaltask.start"}


def create_event_end() -> types.ExternalTaskEndEvent:
    """
    Create an event to indicate the end of an external task processing.
    """
    return {"type": "externaltask.end"}


def create_event_lock_request() -> types.ExternalTaskLockRequestEvent:
    """
    Create an event to request a lock.
    """
    return {"type": "externaltask.lock.request"}


def create_event_lock_accept(lock_duration: int) -> types.ExternalTaskLockAcceptEvent:
    """
    Create an event to accept the lock request.
    """
    return {"type": "externaltask.lock.accept", "lock_duration": lock_duration}


def create_event_lock_reject(
    reason_code: Literal["NOT_IMPLEMENTED", "RESOURCE_UNAVAILABLE", "CUSTOM"],
    reason_message: str,
) -> types.ExternalTaskLockRejectEvent:
    """
    Create an event to reject the lock request.
    """
    return {
        "type": "externaltask.lock.reject",
        "reason_code": reason_code,
        "reason_message": reason_message,
    }


def create_event_execute_request() -> types.ExternalTaskExecuteRequestEvent:
    """
    Create an event to request execution.
    """
    return {"type": "externaltask.execute.request"}


def create_event_execute_reject(
    reason_code: Literal["NOT_IMPLEMENTED", "RESOURCE_UNAVAILABLE", "CUSTOM"],
    reason_message: str,
) -> types.ExternalTaskExecuteRejectEvent:
    """
    Create an event to reject the execute request.
    """
    return {
        "type": "externaltask.execute.reject",
        "reason_code": reason_code,
        "reason_message": reason_message,
    }


def create_event_execute_accept(
    required_variables: set[str] | None = None,
) -> types.ExternalTaskExecuteAcceptEvent:
    """
    Create an event to accept the execute request.

    The required_variables parameter defaults to None
    so that all variables get fetched and returned.
    """
    return {
        "type": "externaltask.execute.accept",
        "required_variables": required_variables,
    }


def create_event_execute_start(
    variables: dict[str, types.Any],
) -> types.ExternalTaskExecuteStartEvent:
    """
    Create an event to start the execution.
    """
    return {
        "type": "externaltask.execute.start",
        "variables": variables,
    }


def create_event_execute_complete(
    variables: dict[str, types.Any] | None = None,
) -> types.ExternalTaskExecuteCompleteEvent:
    """
    Create an event to complete the execute request.
    """
    return {
        "type": "externaltask.execute.complete",
        "variables": variables,
    }


def create_event_execute_abort() -> types.ExternalTaskExecuteAbortEvent:
    """
    Create an event to abort the external task
    """
    return {"type": "externaltask.execute.abort"}


def create_event_execute_failure(
    error_message: str | None = None,
    error_details: str | None = None,
    retries: int | None = None,
    retry_timeout: int | None = None,
    variables: dict[str, types.Any] | None = None,
    local_variables: dict[str, types.Any] | None = None,
) -> types.ExternalTaskExecuteFailureEvent:
    """
    Create an event to reject the execute request.
    """
    return {
        "type": "externaltask.execute.failure",
        "error_message": error_message,
        "error_details": error_details,
        "retries": retries,
        "retry_timeout": retry_timeout,
        "variables": variables,
        "local_variables": local_variables,
    }


def create_event_execute_business_error(
    error_code: str | None = None,
    error_message: str | None = None,
    variables: dict[str, types.Any] | None = None,
) -> types.ExternalTaskExecuteBusinessErrorEvent:
    """
    Create an event to reject the execute request.
    """
    return {
        "type": "externaltask.execute.error",
        "error_code": error_code,
        "error_message": error_message,
        "variables": variables,
    }


def create_lifespan_scope(state: dict[str, Any] | None = None) -> types.LifespanScope:
    return {
        "type": "lifespan",
        "aetpi": {"version": "1.0", "spec_version": "1.0"},
        "state": state or {},
    }


def create_externaltask_scope(task: types.TaskScope) -> types.ExternalTaskScope:
    return {
        "type": "externaltask",
        "protocol": "camunda7",
        "aetpi": {"version": "1.0", "spec_version": "1.0"},
        "task": task,
    }


def create_capabilities_scope(
    state: dict[str, Any] | None = None,
) -> types.CapabilitiesScope:
    return {
        "type": "capabilities",
        "aetpi": {"version": "1.0", "spec_version": "1.0"},
        "state": state or {},
    }


def create_capabilities_request_event() -> types.CapabilitiesRequestEvent:
    return {
        "type": "capabilities.request",
    }


def create_capabilities_response_event(
    capabilities: list | None = None,
) -> types.CapabilitiesResponseEvent:
    return {"type": "capabilities.response", "capabilities": capabilities or []}
