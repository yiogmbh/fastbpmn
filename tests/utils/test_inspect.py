from unittest.mock import MagicMock

import pytest

from fastbpmn.context import Context
from fastbpmn.models import BaseInputModel
from fastbpmn.task import Task, TaskProperties
from fastbpmn.utils.inspect import is_async_callable, map_params


class DummyInput(BaseInputModel):
    some_value: str = "Hello"


def no_arg_handler():
    pass


def none_arg_handler(no_value: None):
    pass


def task_only_handler(task: Task):
    pass


def task_props_only_handler(task_props: TaskProperties):
    pass


def task_and_props_handler(task: Task, task_props: TaskProperties):
    pass


def input_model_handler(value: DummyInput):
    pass


def context_only_handler(arbitrary: Context):
    pass


def full_handler(
    ctx: Context, task: Task, task_props: TaskProperties, value: DummyInput
):
    pass


mocked_task = MagicMock(Task)
mocked_props = MagicMock(TaskProperties)
dummy_input = DummyInput()
mocked_context = MagicMock(Context)


@pytest.mark.parametrize(
    "func,expected_params",
    [
        pytest.param(no_arg_handler, {}, id="no args"),
        pytest.param(none_arg_handler, {"no_value": None}, id="none args"),
        pytest.param(task_only_handler, {"task": mocked_task}, id="task only"),
        pytest.param(
            task_props_only_handler, {"task_props": mocked_props}, id="task props only"
        ),
        pytest.param(
            task_and_props_handler,
            {"task": mocked_task, "task_props": mocked_props},
            id="task and props",
        ),
        pytest.param(
            input_model_handler, {"value": dummy_input}, id="input model only"
        ),
        pytest.param(
            context_only_handler, {"arbitrary": mocked_context}, id="context only"
        ),
        pytest.param(
            full_handler,
            {
                "ctx": mocked_context,
                "value": dummy_input,
                "task": mocked_task,
                "task_props": mocked_props,
            },
            id="full handler",
        ),
    ],
)
def test_map_params(func, expected_params):

    params = map_params(
        func,
        context=mocked_context,
        input_model=dummy_input,
        task=mocked_task,
        task_properties=mocked_props,
    )

    assert params == expected_params


def test_is_async_callable():
    async def is_async():
        return

    def is_sync():
        return

    assert is_async_callable(is_async) is True
    assert is_async_callable(is_sync) is False
