from typing import Annotated

from pydantic import BeforeValidator, Field

"""
The timeout between subsequent tries of external tasks in 100 millisecond accuracy (e.g. 400 or 1300)
"""
TaskTimeout = Annotated[int, Field(ge=0, multiple_of=100)]

"""
A type declaration for number of retries of an external task (greater or equal to 0)
"""
TaskRetries = Annotated[int, Field(ge=0, multiple_of=1)]


def ensure_default_value(value: int | None) -> int:
    """
    Ensure that a value is not None and return it.

    :param value: The value to check
    :return: The value if it is not None
    :raises ValueError: If the value is None
    """
    if value is None:
        return 300_000

    return value


LockDuration = Annotated[
    int, BeforeValidator(ensure_default_value), Field(ge=0, multiple_of=100)
]


__all__ = ["TaskTimeout", "TaskRetries", "LockDuration"]
