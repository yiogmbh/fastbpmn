from dataclasses import dataclass
from typing import Callable, Any

from .process_instance import ProcessInstance
from .task import Task


__all__ = [
    "ProcessInstance",
    "Task",
    "Depends",
    "InputVariable",
    "InputModel",
]


@dataclass(frozen=True)
class Depends:
    """
    Annotation to allow specifying callable dependencies

    Should support:
    - callable
    - coroutines
    - context managers
    - async contextmanager
    """

    dependency: Callable[..., Any] | None = None
    use_cache: bool = True


@dataclass(frozen=True)
class InputVariable:
    """
    Annotation to allow getting a variable by name
    """

    alias: str | None = None
    # todo: maybe one might to specify the type as well


@dataclass(frozen=True)
class InputModel:
    """
    Annotation to allow parsing input variables using pydantic (e.g. typed dict, models, ...)

    Uses pydantic's TypeAdapter internally to parse input variables
    """

    # todo: may we need to specify model type
