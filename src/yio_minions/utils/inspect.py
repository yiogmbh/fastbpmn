import asyncio
import functools
import inspect
import typing
from typing import Any, Callable, Dict, Optional

from yio_minions.context import Context
from yio_minions.task import Task, TaskProperties

__all__ = ["is_async_callable", "map_params"]


def map_params(
    func: Callable[[Any], Any],
    input_model: Optional[Any],
    task: Task,
    task_properties: TaskProperties,
    context: Context,
) -> Dict[str, Any]:

    signature = inspect.signature(func)
    parameters = signature.parameters

    mapped_params = {}

    for arg_name, arg_class in parameters.items():
        # Try to pass Task and TaskProperties whenever required.
        if arg_class.annotation == Task:
            mapped_params[arg_name] = task

        if arg_class.annotation == TaskProperties:
            mapped_params[arg_name] = task_properties

        if arg_class.annotation == Context:
            mapped_params[arg_name] = context

        # Try to figure out which named argument should be used for the input_model data
        if input_model and arg_class.annotation is type(input_model):
            mapped_params[arg_name] = input_model

        # This case is used for situations where a method is defined like
        # def method(unused: None, task: Task): ....
        # meaning that we have to pass something for unused param
        if arg_class.annotation is None:
            mapped_params[arg_name] = None

    return mapped_params


def is_async_callable(obj: typing.Any) -> bool:
    while isinstance(obj, functools.partial):
        obj = obj.func

    return asyncio.iscoroutinefunction(obj) or (
        callable(obj) and asyncio.iscoroutinefunction(obj.__call__)
    )


def get_method_name(func: Callable[[Any], Any]) -> str:
    return func.__name__


def get_method_doc(func: Callable[[Any], Any]) -> Optional[str]:
    return inspect.getdoc(func)
