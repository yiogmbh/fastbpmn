from typing import Any, Optional

from yio_minions.errors.context import _extract_endpoint_context


class FastBpmnError(Exception):
    """
    Base exception to handle
    """


# Legacy support
YioMinionError = FastBpmnError


class ExternalTaskError(YioMinionError):
    """
    A base exception that is used to determine errors with external tasks
    """

    __slots__ = ["detailed_message"]

    def __init__(self, *args: object, detailed_message: Optional[str] = None) -> None:
        super().__init__(*args)
        self.detailed_message = detailed_message or str(self)


class DuplicateTaskHandlerError(FastBpmnError):
    def __init__(
        self, predicate_repr: str, existing_handler: Any, duplicate_handler: Any
    ) -> None:

        super().__init__(f"""
Duplicate handler for {predicate_repr}

* existing:
    {existing_handler.__module__}.{existing_handler.__name__}
    {_extract_endpoint_context(existing_handler)}
* duplicate:
    {duplicate_handler.__module__}.{duplicate_handler.__name__}
    {_extract_endpoint_context(duplicate_handler)}
""")
