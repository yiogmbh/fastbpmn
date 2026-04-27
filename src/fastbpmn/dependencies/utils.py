import asyncio
import functools
import inspect
from contextlib import AsyncExitStack, contextmanager
from inspect import Parameter
from typing import Callable, Any

from pydantic import BaseModel, TypeAdapter
from typing_extensions import is_typeddict

from fastbpmn.context import Context
from fastbpmn.params import ProcessInstance, Task, Depends
from fastbpmn.task import TaskProperties
from fastbpmn.utils.concurrency import (
    run_in_threadpool,
    contextmanager_in_threadpool,
    asynccontextmanager,
)
from . import models as m


def build_dependant(
    call: Callable[..., Any], name: str | None = None
) -> m.Dependant | None:
    """

    :param call:
    :return:
    """
    signature = inspect.signature(call)
    parameters = signature.parameters

    vals = {
        "builtins": [],
        "input_variables": [],
        "input_models": [],
        "sub_dependencies": [],
    }

    for arg_name, arg_class in parameters.items():
        # before we should check if default value is a "Depends" or so
        if is_subdependency(arg_class):
            depends: Depends = arg_class.default
            vals["sub_dependencies"].append(
                build_dependant(name=arg_name, call=depends.dependency)
            )

        # first we check for type hint indicating a builtin
        if arg_class.annotation in (ProcessInstance, Task, Context, TaskProperties):
            vals["builtins"].append(
                m.BuiltinTypeDependant(name=arg_name, clazz=arg_class.annotation)
            )

        elif issubclass(arg_class.annotation, (BaseModel,)) or is_typeddict(
            arg_class.annotation
        ):
            adapter = TypeAdapter(arg_class.annotation)
            vals["input_models"].append(
                m.InputModelDependant(
                    name=arg_name, clazz=arg_class.annotation, adapter=adapter
                )
            )

        # probably we get to point where only variable dependant remains
        else:
            vals["input_variables"].append(
                as_input_variable_dependant(arg_name, arg_class)
            )

    return m.Dependant(name=name, call=call, **vals)


async def resolve_dependencies(
    dependant: m.Dependant,
    *,
    variables: dict[str, Any],
    builtins: m.Builtins,
    exit_stack: AsyncExitStack,
    dependency_cache: dict[m.DependencyCacheKey, Any] | None = None,
) -> m.ResolvedDependant:

    values_builtin = _resolve_builtin_dependants(
        dependant.builtins,
        builtins=builtins,
    )
    values_vars = _resolve_input_variables(dependant.input_variables, variables)
    values_models = _resolve_input_models(dependant.input_models, variables)

    values_calls = {}
    dependency_cache = dependency_cache or {}
    # iterating sub dependencies to get resolved deps
    for sub_dep in dependant.sub_dependencies:
        sub_resolved = await resolve_dependencies(
            sub_dep,
            variables=variables,
            builtins=builtins,
            exit_stack=exit_stack,
            dependency_cache=dependency_cache,
        )

        if sub_dep.use_cache and sub_dep.cache_key in dependency_cache:
            sub_result = dependency_cache[sub_dep.cache_key]
        elif sub_dep.is_gen_callable:
            sub_result = await _resolve_yield_dependants(
                sub_dep, values=sub_resolved.kwargs, stack=exit_stack
            )
        elif sub_dep.is_async_gen_callable:
            sub_result = await _resolve_yield_dependants(
                sub_dep, values=sub_resolved.kwargs, stack=exit_stack
            )
        elif sub_dep.is_coroutine_callable:
            sub_result = await sub_dep.call(**sub_resolved.kwargs)
        else:
            # run in thread pool (synchronous function alike)
            sub_result = await run_in_threadpool(sub_dep.call, **sub_resolved.kwargs)

        if sub_dep.cache_key not in dependency_cache:
            dependency_cache[sub_dep.cache_key] = sub_result

        values_calls[sub_dep.name] = sub_result

    # todo implement depends substuff
    values = values_builtin | values_vars | values_models | values_calls

    return m.ResolvedDependant(kwargs=values, cache=dependency_cache)


async def _resolve_yield_dependants(
    dep: m.Dependant,
    *,
    values: dict[str, Any],
    stack: AsyncExitStack,
) -> Any:
    if dep.is_async_gen_callable:
        cm = asynccontextmanager(dep.call)(**values)
    elif dep.is_gen_callable:
        cm = contextmanager_in_threadpool(contextmanager(dep.call)(**values))
    return await stack.enter_async_context(cm)


def _resolve_builtin_dependants(
    deps: list[m.BuiltinTypeDependant], *, builtins: m.Builtins
) -> dict[str, Any]:
    return {dep.name: _resolve_builtin_dependant(dep, **builtins) for dep in deps}


def _resolve_builtin_dependant(
    dep: m.BuiltinTypeDependant,
    *,
    context: Context,
    task_properties: TaskProperties,
    task: Task,
    process_instance: ProcessInstance,
) -> Any:
    if dep.clazz == Context:
        return context
    if dep.clazz == Task:
        return task
    if dep.clazz == ProcessInstance:
        return process_instance
    if dep.clazz == TaskProperties:
        return task_properties

    raise NotImplementedError(
        f"{dep.clazz} is not an implemented builtin (should not happen)."
    )


def _resolve_input_models(
    deps: list[m.InputModelDependant], variables: dict[str, Any]
) -> dict[str, Any]:
    return {dep.name: _resolve_input_model(dep, variables) for dep in deps}


def _resolve_input_model(
    dep: m.InputModelDependant,
    variables: dict[str, Any],
) -> Any:
    # TODO may be we need appropriate exceptions ..
    return dep.adapter.validate_python(variables)


def _resolve_input_variables(
    deps: list[m.InputVariableDependant],
    variables: dict[str, Any],
) -> dict[str, Any]:
    return {dep.name: _resolve_input_variable(dep, variables) for dep in deps}


def _resolve_input_variable(
    dep: m.InputVariableDependant,
    variables: dict[str, Any],
) -> Any:
    if dep.alias not in variables and dep.has_default:
        return dep.default_value

    if dep.alias in variables:
        return variables[dep.alias]

    raise NotImplementedError(f"{dep.name} / {dep.alias} not resolved")


def is_subdependency(
    arg_parameter: inspect.Parameter,
) -> bool:
    return isinstance(arg_parameter.default, Depends)


def is_async_callable(obj: Any) -> bool:
    while isinstance(obj, functools.partial):
        obj = obj.func

    return asyncio.iscoroutinefunction(obj) or (
        callable(obj) and asyncio.iscoroutinefunction(obj.__call__)
    )


def as_input_variable_dependant(
    arg_name: str, arg_parameter: Parameter
) -> m.InputVariableDependant:

    adapter = TypeAdapter(arg_parameter.annotation)

    has_default = arg_parameter.default is not inspect.Parameter.empty
    default_value = arg_parameter.default if has_default else None

    return m.InputVariableDependant(
        name=arg_name,
        alias=arg_name,
        clazz=arg_parameter.annotation,
        adapter=adapter,
        has_default=has_default,
        default_value=default_value,
    )
