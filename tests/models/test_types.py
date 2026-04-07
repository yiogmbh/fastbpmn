from typing import Any, Type
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from fastbpmn.context import Context
from fastbpmn.models.base import FileInfo
from fastbpmn.models.types.camunda7 import (
    Camunda7Boolean,
    Camunda7Double,
    Camunda7Integer,
    Camunda7Json,
    Camunda7Null,
    Camunda7Primitive,
    Camunda7String,
    Camunda7TypeAdapter,
    Camunda7VariableAdapter,
    preprocess_var_dict,
    read_variables,
)
from fastbpmn.task import Task


@pytest.mark.parametrize(
    "input, TargetType, name, expected",
    [
        pytest.param(
            {"name": "test", "type": "integer", "value": "1"},
            Camunda7Integer,
            "test",
            1,
            id="int",
        ),
    ],
)
def test_camunda7types(input: dict, TargetType: Type, name: str, expected: Any):

    variable = TargetType(**input)

    assert variable.value == expected
    assert variable.name == name


@pytest.mark.parametrize(
    "input, expected_type, expected_name, expected_value",
    [
        pytest.param(
            {"name": "test", "type": "integer", "value": "1"},
            Camunda7Integer,
            "test",
            1,
            id="int",
        ),
        pytest.param(
            {"name": "test", "type": "Double", "value": "1.82"},
            Camunda7Double,
            "test",
            1.82,
            id="double",
        ),
        pytest.param(
            {"name": "test", "type": "boolean", "value": False},
            Camunda7Boolean,
            "test",
            False,
            id="bool",
        ),
        pytest.param(
            {"name": "test", "type": "string", "value": None},
            Camunda7String,
            "test",
            None,
            id="string (none)",
        ),
        pytest.param(
            {"name": "test", "type": "String", "value": "False"},
            Camunda7String,
            "test",
            "False",
            id="string",
        ),
        pytest.param(
            {"name": "test", "type": "Null", "value": None},
            Camunda7Null,
            "test",
            None,
            id="null",
        ),
    ],
)
def test_camunda7_variable_type_adapter(
    input: dict,
    expected_type: Type[Camunda7Primitive],
    expected_name: str,
    expected_value: Any,
):

    camunda_variable = Camunda7TypeAdapter.validate_python(input)

    assert isinstance(camunda_variable, expected_type)
    assert camunda_variable.value == expected_value
    assert camunda_variable.name == expected_name


@pytest.mark.parametrize(
    "input, expected_result",
    [
        pytest.param(
            {"test": {"type": "integer", "value": "1"}},
            [Camunda7Integer(name="test", type="integer", value=1)],
            id="int",
        ),
        pytest.param(
            {"test": {"type": "Double", "value": "1.82"}},
            [Camunda7Double(name="test", type="Double", value=1.82)],
            id="double",
        ),
        pytest.param(
            {"test": {"type": "boolean", "value": False}},
            [Camunda7Boolean(name="test", type="boolean", value=False)],
            id="bool",
        ),
        pytest.param(
            {"test": {"type": "string", "value": None}},
            [Camunda7String(name="test", type="string", value=None)],
            id="string (none)",
        ),
        pytest.param(
            {"test": {"type": "String", "value": "False"}},
            [Camunda7String(name="test", type="String", value="False")],
            id="string",
        ),
        pytest.param(
            {"test": {"type": "json", "value": '{"test": "value"}'}},
            [Camunda7Json(name="test", type="json", value='{"test": "value"}')],
            id="json",
        ),
        pytest.param(
            {
                "test": {"type": "json", "value": '{"test": "value"}'},
                "test2": {"type": "String", "value": "False"},
            },
            [
                Camunda7Json(name="test", type="json", value='{"test": "value"}'),
                Camunda7String(name="test2", type="String", value="False"),
            ],
            id="Multiple",
        ),
    ],
)
def test_camunda7_variables_adapter(input: dict, expected_result: dict):

    preprocessed = preprocess_var_dict(input)

    camunda_variables = Camunda7VariableAdapter.validate_python(preprocessed)

    assert camunda_variables == expected_result


@pytest.mark.parametrize(
    "input, expected_result",
    [
        pytest.param(
            {"test": {"type": "integer", "value": "1"}}, {"test": 1}, id="int"
        ),
        pytest.param(
            {
                "file": {
                    "type": "File",
                    "valueInfo": {
                        "filename": "hello.pdf",
                        "mimetype": "application/pdf",
                    },
                }
            },
            {
                "file": FileInfo(
                    filename="hello.pdf",
                    mimetype="application/pdf",
                    sync_download=lambda: None,
                )
            },
            id="file var",
        ),
    ],
)
def test_read_variables(input: dict, expected_result: dict):

    mocked_context = MagicMock(Context)
    mocked_task = MagicMock(Task)

    context = {"context": mocked_context, "task": mocked_task}

    with patch(
        "fastbpmn.models.types.camunda7.to_sync_callback"
    ) as mocked_sync_callback:

        def callback():
            return None

        mocked_sync_callback.return_value = callback
        if isinstance(expected_result, FileInfo):
            expected_result.sync_download = callback

        minion_variables = read_variables(input, context)

    for key, value in expected_result.items():
        assert key in minion_variables
        assert isinstance(minion_variables.get(key), type(value))


@pytest.mark.parametrize(
    "input",
    [
        pytest.param({"test": {"type": "bigint", "value": "1"}}, id="bigint"),
    ],
)
def test_unknown_datatype(input: dict):
    mocked_context = MagicMock(Context)
    mocked_task = MagicMock(Task)

    context = {"context": mocked_context, "task": mocked_task}

    with pytest.raises(ValidationError):
        read_variables(input, context)
