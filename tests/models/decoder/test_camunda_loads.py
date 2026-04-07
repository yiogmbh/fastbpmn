from unittest import mock
from unittest.mock import MagicMock

import pytest

from fastbpmn.context import Context
from fastbpmn.errors import DatatypeNotSupported
from fastbpmn.models import FileInfo
from fastbpmn.models.decoder import camunda_loads
from fastbpmn.task import Task


@pytest.fixture()
def mocked_context():
    mocked_context = MagicMock(Context)
    yield mocked_context


@pytest.fixture()
def mocked_task():
    mocked_task = MagicMock(Task)

    mocked_task.file_variable_sync.return_value = b"ABCDEFG"

    yield mocked_task


def mocked_sync_callback():
    return None


@pytest.mark.parametrize(
    "camunda_variables,kwargs_variables",
    [
        pytest.param(
            {"var_a": {"type": "string", "value": "Hello"}},
            {"var_a": "Hello"},
            id="String Variable",
        ),
        pytest.param(
            {"var_a": {"type": "integer", "value": 1903}},
            {"var_a": 1903},
            id="Integer Variable",
        ),
        pytest.param(
            {"var_a": {"type": "Null", "value": None}}, {"var_a": None}, id="NULL Type"
        ),
        pytest.param(
            {"data_file": {"type": "String", "value": None, "valueInfo": {}}},
            {"data_file": None},
            id="none string",
        ),
        pytest.param(
            {"null_variable": {"value": None, "type": "Null"}},
            {"null_variable": None},
            id="null variable",
        ),
        pytest.param(
            {"boolean_variable": {"value": True, "type": "Boolean"}},
            {"boolean_variable": True},
            id="boolean variable",
        ),
        pytest.param(
            {"integer_variable": {"value": 1, "type": "Integer"}},
            {"integer_variable": 1},
            id="integer variable",
        ),
        pytest.param(
            {"short_variable": {"value": 1, "type": "Short"}},
            {"short_variable": 1},
            id="short variable",
        ),
        pytest.param(
            {"long_variable": {"value": 1, "type": "Long"}},
            {"long_variable": 1},
            id="long variable",
        ),
        pytest.param(
            {"double_variable": {"value": 1.0, "type": "Double"}},
            {"double_variable": 1.0},
            id="double variable",
        ),
        pytest.param(
            {"string_variable": {"value": "test", "type": "String"}},
            {"string_variable": "test"},
            id="string variable",
        ),
        pytest.param(
            {"json_variable": {"value": '{"test": "test"}', "type": "Json"}},
            {"json_variable": {"test": "test"}},
            id="json variable",
        ),
        pytest.param(
            {"file_variable": {"value": None, "type": "File"}},
            {
                "file_variable": FileInfo(
                    variable_name="file_variable", sync_download=mocked_sync_callback
                )
            },
            id="file variable (no valueInfo)",
        ),
        pytest.param(
            {
                "file_variable": {
                    "value": None,
                    "type": "File",
                    "valueInfo": {
                        "filename": "test.pdf",
                        "mimetype": "application/octet-stream",
                        "encoding": "UTF-8",
                    },
                }
            },
            {
                "file_variable": FileInfo(
                    filename="test.pdf",
                    mimetype="application/octet-stream",
                    encoding="UTF-8",
                    variable_name="file_variable",
                    sync_download=mocked_sync_callback,
                )
            },
            id="file variable (full valueInfo)",
        ),
    ],
)
@mock.patch("fastbpmn.models.types.camunda7.to_sync_callback")
def test_camunda_loads(
    mocked_to_sync, mocked_context, camunda_variables, kwargs_variables
):

    mocked_to_sync.return_value = mocked_sync_callback
    result = camunda_loads(mocked_context, variables=camunda_variables, task=None)

    assert result == kwargs_variables


@pytest.mark.skip
def test_unsupported(mocked_context, mocked_task):

    with pytest.raises(DatatypeNotSupported) as exc_info:
        camunda_loads(
            mocked_context,
            {"null_variable": {"value": None, "type": "WhatANotExistingType"}},
            task=mocked_task,
        )

    assert str(exc_info.value).startswith(
        "Unsupported DataTypes detected. \n\nErrors: \n"
    )
