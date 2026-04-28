import inspect
from dataclasses import dataclass, field
from functools import partial, cached_property
from typing import Generic, TypeVar, Callable, Any, Self, ParamSpec

from aetpiref.typing import ExternalTaskScope
from typing_extensions import TypedDict
from pydantic import TypeAdapter

from fastbpmn.context import Context
from fastbpmn.task import TaskProperties
from fastbpmn.params import Task, ProcessInstance

P = ParamSpec("P")
T = TypeVar("T")
TVar = TypeVar("TVar")
TBuiltinType = TypeVar("TBuiltinType", Context, Task, ProcessInstance, TaskProperties)
DependencyCacheKey = tuple[Callable[..., Any] | None]
# tuple[Callable[..., Any] | None, tuple[str, ...] | None, str | None]


class Builtins(TypedDict, total=True):
    context: Context
    task: Task
    process_instance: ProcessInstance
    task_properties: TaskProperties
    scope: ExternalTaskScope


def _unwrapped_call(call: Callable[..., Any] | None) -> Any:
    if call is None:
        return call  # pragma: no cover
    unwrapped = inspect.unwrap(_impartial(call))
    return unwrapped


def _impartial(func: Callable[..., Any]) -> Callable[..., Any]:
    while isinstance(func, partial):
        func = func.func
    return func


@dataclass(frozen=True)
class InputVariableDependant(Generic[TVar]):
    # name defines the argument name on calling
    name: str
    # the name of the process variable to use
    alias: str
    clazz: type[TVar]
    # the type adapter instance to decode the variable
    adapter: TypeAdapter[TVar]

    has_default: bool = False
    default_value: TVar | None = None


@dataclass(frozen=True)
class InputModelDependant(Generic[TVar]):
    name: str
    clazz: type[TVar]
    adapter: TypeAdapter[TVar]


@dataclass(frozen=True)
class BuiltinTypeDependant(Generic[TBuiltinType]):
    name: str
    clazz: type[TBuiltinType]


@dataclass(frozen=True)
class Dependant:
    name: str | None  # if its "top-most" this is ok to be none
    call: Callable[P, T] | None = None

    input_variables: list[InputVariableDependant] = field(default_factory=list)
    input_models: list[InputModelDependant] = field(default_factory=list)
    builtins: list[BuiltinTypeDependant] = field(default_factory=list)
    sub_dependencies: list[Self] = field(default_factory=list)

    use_cache: bool = True

    @cached_property
    def cache_key(self) -> DependencyCacheKey:
        return (self.call,)

    @cached_property
    def is_gen_callable(self) -> bool:
        if self.call is None:
            return False  # pragma: no cover
        if inspect.isgeneratorfunction(
            _impartial(self.call)
        ) or inspect.isgeneratorfunction(_unwrapped_call(self.call)):
            return True
        if inspect.isclass(_unwrapped_call(self.call)):
            return False
        dunder_call = getattr(_impartial(self.call), "__call__", None)  # noqa: B004
        if dunder_call is None:
            return False  # pragma: no cover
        if inspect.isgeneratorfunction(
            _impartial(dunder_call)
        ) or inspect.isgeneratorfunction(_unwrapped_call(dunder_call)):
            return True
        dunder_unwrapped_call = getattr(_unwrapped_call(self.call), "__call__", None)  # noqa: B004
        if dunder_unwrapped_call is None:
            return False  # pragma: no cover
        if inspect.isgeneratorfunction(
            _impartial(dunder_unwrapped_call)
        ) or inspect.isgeneratorfunction(_unwrapped_call(dunder_unwrapped_call)):
            return True
        return False

    @cached_property
    def is_async_gen_callable(self) -> bool:
        if self.call is None:
            return False  # pragma: no cover
        if inspect.isasyncgenfunction(
            _impartial(self.call)
        ) or inspect.isasyncgenfunction(_unwrapped_call(self.call)):
            return True
        if inspect.isclass(_unwrapped_call(self.call)):
            return False
        dunder_call = getattr(_impartial(self.call), "__call__", None)  # noqa: B004
        if dunder_call is None:
            return False  # pragma: no cover
        if inspect.isasyncgenfunction(
            _impartial(dunder_call)
        ) or inspect.isasyncgenfunction(_unwrapped_call(dunder_call)):
            return True
        dunder_unwrapped_call = getattr(_unwrapped_call(self.call), "__call__", None)  # noqa: B004
        if dunder_unwrapped_call is None:
            return False  # pragma: no cover
        if inspect.isasyncgenfunction(
            _impartial(dunder_unwrapped_call)
        ) or inspect.isasyncgenfunction(_unwrapped_call(dunder_unwrapped_call)):
            return True
        return False

    @cached_property
    def is_coroutine_callable(self) -> bool:
        if self.call is None:
            return False  # pragma: no cover
        if inspect.isroutine(_impartial(self.call)) and inspect.iscoroutinefunction(
            _impartial(self.call)
        ):
            return True
        if inspect.isroutine(
            _unwrapped_call(self.call)
        ) and inspect.iscoroutinefunction(_unwrapped_call(self.call)):
            return True
        if inspect.isclass(_unwrapped_call(self.call)):
            return False
        dunder_call = getattr(_impartial(self.call), "__call__", None)  # noqa: B004
        if dunder_call is None:
            return False  # pragma: no cover
        if inspect.iscoroutinefunction(
            _impartial(dunder_call)
        ) or inspect.iscoroutinefunction(_unwrapped_call(dunder_call)):
            return True
        dunder_unwrapped_call = getattr(_unwrapped_call(self.call), "__call__", None)  # noqa: B004
        if dunder_unwrapped_call is None:
            return False  # pragma: no cover
        if inspect.iscoroutinefunction(
            _impartial(dunder_unwrapped_call)
        ) or inspect.iscoroutinefunction(_unwrapped_call(dunder_unwrapped_call)):
            return True
        return False


@dataclass(frozen=True)
class ResolvedDependant:
    kwargs: dict[str, Any]
    cache: dict[DependencyCacheKey, Any]
