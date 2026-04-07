from typing import Optional

from .base import ExternalTaskError
from .types import Retries, RetryTimeout


class RetryExternalTask(ExternalTaskError):
    """
    An error indicating that an external task should be retried
    because the error will go away automatically.
    """

    __slots__ = ["retries", "retry_timeout"]

    def __init__(
        self,
        *args: object,
        detailed_message: Optional[str] = None,
        retries: Optional[
            Retries
        ] = None,  # Explicitly None to make retries work as expected
        retry_timeout: Optional[
            RetryTimeout
        ] = None,  # Explicitly None to make retry_timeout work as expected
    ) -> None:
        super().__init__(*args, detailed_message=detailed_message)
        self.retries = retries
        self.retry_timeout = retry_timeout


class AbortExternalTask(ExternalTaskError):
    """
    An external task gets aborted without even notice the process engine

    This can be useful for debugging purpose.
    It's recommended to use the message/cause of this exception to specify
    why you wanted to perform an abortion.
    """


class FatalExternalTaskError(ExternalTaskError):
    """
    A base class to indicate a fatal error while executing an external task

    Usually this error occurs whenever an unexpected and unhandled exception
    interrupts the external task execution
    """
