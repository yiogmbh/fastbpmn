"""
Business Errors:
A bunch of errors to indicate errors related to a business process and not due to invalid resources.

A good example is here:
https://blog.viadee.de/en/camunda-external-tasks-error-handling-and-retry-behavior

"""

from typing import TYPE_CHECKING, Optional

from .base import ExternalTaskError

if TYPE_CHECKING:
    from ..model import OutputModel


class TaskBusinessError(ExternalTaskError):
    """
    A base implementation for business errors. It's recommended to inherit this class to specify
    error codes specific to your business process
    """

    __slots__ = ["error_code", "variables"]

    def __init__(
        self,
        *args: object,
        error_code: str,
        variables: Optional["OutputModel"] = None,
        detailed_message: Optional[str] = None,
    ) -> None:
        super().__init__(*args, detailed_message=detailed_message)
        self.error_code = error_code
        self.variables = variables
