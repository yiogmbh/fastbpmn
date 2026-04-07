from typing import Optional

from .base import ExternalTaskError


class ProcessEngineError(ExternalTaskError):
    """
    Errors that are related to the process engine.
    """

    __slots__ = ["exception_type"]

    def __init__(
        self,
        *args: object,
        detailed_message: Optional[str] = None,
        exception_type: Optional[str] = None,
    ) -> None:
        super().__init__(*args, detailed_message=detailed_message)
        self.exception_type = exception_type


class TaskFetchError(ProcessEngineError):
    """
    Indicates errors occurring while task preparation (fetch and lock phase).
    """


class FetchAndLockFailed(TaskFetchError):
    """
    Indicates that fetching an external task was not successful.
    """


class InputDataValidationError(TaskFetchError):
    """
    Indicates that a task cannot be processed due to input data validation error.
    That means, that the input data do not match the pydantic input models expectations.
    """


class OutputDataValidationError(TaskFetchError):
    """
    Indicates that a task cannot be processed due to output data validation error.
    That means, that the input data do not match the pydantic input models expectations.
    """


class DatatypeNotSupported(ProcessEngineError):
    """
    Indicates that a datatype is currently not supported to be used with yio-minions
    """


class TaskCompleteFailed(ProcessEngineError):
    """
    Indicates that the task cannot be completed (error from camunda api).
    """


class TaskStateError(ProcessEngineError):
    """
    Indicates errors in case of invalid task states.
    """
