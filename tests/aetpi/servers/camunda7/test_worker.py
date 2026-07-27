from unittest.mock import AsyncMock, MagicMock

import pytest

from fastbpmn.aetpi.servers.camunda7.worker import Camunda7ServerWorker


@pytest.fixture()
def worker():
    process_engine = MagicMock()
    process_engine.process_instance_execution_ids = AsyncMock()
    app = AsyncMock()
    return Camunda7ServerWorker(process_engine=process_engine, app=app)


@pytest.mark.asyncio
async def test_fetch_file_variable_uses_hierarchy(worker):
    worker.process_engine.process_instance_execution_ids.return_value = [
        "exec-root",
        "exec-child",
        "exec-leaf",
    ]
    worker.process_engine.external_task_execution_file_variable = AsyncMock()
    worker.process_engine.external_task_execution_file_variable.side_effect = [
        (False, None),
        (False, None),
        (True, b"leaf data"),
    ]

    result = await worker._fetch_file_variable(
        process_instance_id="pi-1",
        execution_id="exec-leaf",
        variable_name="my_var",
    )

    assert result == b"leaf data"
    worker.process_engine.process_instance_execution_ids.assert_awaited_once_with(
        process_instance_id="pi-1",
        execution_id="exec-leaf",
    )
    assert worker.process_engine.external_task_execution_file_variable.await_count == 3


@pytest.mark.asyncio
async def test_fetch_file_variable_uses_reversed_order(worker):
    """Narrowest scope should be tried first."""
    worker.process_engine.process_instance_execution_ids.return_value = [
        "exec-root",
        "exec-child",
        "exec-leaf",
    ]
    worker.process_engine.external_task_execution_file_variable = AsyncMock()
    worker.process_engine.external_task_execution_file_variable.side_effect = [
        (True, b"leaf data"),
    ]

    result = await worker._fetch_file_variable(
        process_instance_id="pi-1",
        execution_id="exec-leaf",
        variable_name="my_var",
    )

    assert result == b"leaf data"
    worker.process_engine.external_task_execution_file_variable.assert_awaited_once_with(
        execution_id="exec-leaf",
        variable_name="my_var",
    )


@pytest.mark.asyncio
async def test_fetch_file_variable_all_exhausted(worker):
    worker.process_engine.process_instance_execution_ids.return_value = [
        "exec-root",
        "exec-leaf",
    ]
    worker.process_engine.external_task_execution_file_variable = AsyncMock()
    worker.process_engine.external_task_execution_file_variable.side_effect = [
        (False, None),
        (False, None),
    ]

    result = await worker._fetch_file_variable(
        process_instance_id="pi-1",
        execution_id="exec-leaf",
        variable_name="my_var",
    )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_file_variable_returns_first_hit(worker):
    """Should stop at first successful execution, not continue."""
    worker.process_engine.process_instance_execution_ids.return_value = [
        "exec-root",
        "exec-child",
        "exec-leaf",
    ]
    worker.process_engine.external_task_execution_file_variable = AsyncMock()
    worker.process_engine.external_task_execution_file_variable.side_effect = [
        (False, None),
        (True, b"child data"),
    ]

    result = await worker._fetch_file_variable(
        process_instance_id="pi-1",
        execution_id="exec-leaf",
        variable_name="my_var",
    )

    assert result == b"child data"
    assert worker.process_engine.external_task_execution_file_variable.await_count == 2
