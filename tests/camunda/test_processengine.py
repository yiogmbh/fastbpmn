from unittest.mock import AsyncMock

import httpx
import pytest

from fastbpmn.camunda.processengine import ProcessEngine


@pytest.fixture()
def engine():
    e = ProcessEngine(
        camunda_base_url="http://localhost:8080/engine-rest",
    )
    e.request = AsyncMock()
    return e


@pytest.mark.asyncio
async def test_external_task_execution_file_variable_success(engine):
    engine.request.get_raw.return_value = b"file content"

    success, content = await engine.external_task_execution_file_variable(
        execution_id="exec-1",
        variable_name="my_var",
    )

    assert success is True
    assert content == b"file content"
    engine.request.get_raw.assert_awaited_once_with(
        "/execution/exec-1/localVariables/my_var/data",
        binary=True,
    )


@pytest.mark.asyncio
async def test_external_task_execution_file_variable_not_found(engine):
    engine.request.get_raw.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=httpx.Request(
            "GET",
            "http://localhost:8080/engine-rest/execution/exec-1/localVariables/my_var/data",
        ),
        response=httpx.Response(404),
    )

    success, content = await engine.external_task_execution_file_variable(
        execution_id="exec-1",
        variable_name="my_var",
    )

    assert success is False
    assert content is None


@pytest.mark.asyncio
async def test_external_task_execution_file_variable_bad_request(engine):
    engine.request.get_raw.side_effect = httpx.HTTPStatusError(
        "Bad Request",
        request=httpx.Request(
            "GET",
            "http://localhost:8080/engine-rest/execution/exec-1/localVariables/my_var/data",
        ),
        response=httpx.Response(400),
    )

    success, content = await engine.external_task_execution_file_variable(
        execution_id="exec-1",
        variable_name="my_var",
    )

    assert success is False
    assert content is None
