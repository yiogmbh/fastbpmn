from contextlib import nullcontext as does_not_raise
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastbpmn.context.context import Context
from fastbpmn.context.exceptions import (
    MessageCorrelateError,
    SignalFailureError,
    VariableFetchError,
)
from fastbpmn.context.io import Delete, TempPath
from fastbpmn.context.models import (
    Message,
    MessageFailure,
    MessageResult,
    Signal,
    SignalResult,
)
from fastbpmn.models import FileInfo
from fastbpmn.task import Task


class UnitTestError(Exception):
    """
    Some error defined for unit test usage
    """


@mock.patch("fastbpmn.context.context.delete_all")
@pytest.mark.asyncio
async def test_context_manager_no_op(patched_delete_all):
    async with Context(
        variable_fetcher=AsyncMock(),
        message_correlator=AsyncMock(),
        signal_emitter=AsyncMock(),
    ):
        pass

    patched_delete_all.assert_awaited_once_with(temp_paths=[], error=False)


@pytest.mark.parametrize(
    "error,expectation",
    [
        pytest.param(False, does_not_raise(), id="no error"),
        pytest.param(True, pytest.raises(UnitTestError), id="error"),
    ],
)
@mock.patch("fastbpmn.context.context.create_temp_file")
@mock.patch("fastbpmn.context.context.create_temp_dir")
@mock.patch("fastbpmn.context.context.delete_all")
@pytest.mark.asyncio
async def test_context_manager_with_dirs_and_files(
    patched_delete_all,
    patched_create_temp_dir,
    patched_create_temp_file,
    error,
    expectation,
):
    MagicMock(Task)
    temp_dir = MagicMock(TempPath)
    type(temp_dir).path = MagicMock(Path)
    temp_dir2 = MagicMock(TempPath)
    type(temp_dir2).path = MagicMock(Path)
    temp_file = MagicMock(TempPath)
    type(temp_file).path = MagicMock(Path)
    patched_create_temp_dir.side_effect = [temp_dir, temp_dir2]
    patched_create_temp_file.return_value = temp_file

    with expectation:
        async with Context(
            variable_fetcher=AsyncMock(),
            message_correlator=AsyncMock(),
            signal_emitter=AsyncMock(),
        ) as ctx:
            ctx.temp_dir()
            ctx.temp_file(suffix=".suffix")
            ctx.temp_file_in_dir("myfile.txt")

            if error:
                raise UnitTestError

    patched_create_temp_dir.assert_has_calls(
        [mock.call(flags=Delete.ALWAYS), mock.call(flags=Delete.ALWAYS)]
    )
    patched_create_temp_file.assert_called_once_with(
        flags=Delete.ALWAYS, suffix=".suffix"
    )
    patched_delete_all.assert_awaited_once_with(
        temp_paths=[temp_dir, temp_file, temp_dir2], error=error
    )


@mock.patch("fastbpmn.context.context.Context.temp_file")
@mock.patch("fastbpmn.context.context.Context.temp_file_in_dir")
@pytest.mark.asyncio
async def test_download_file_with_name(
    mocked_temp_file_in_dir: MagicMock, mocked_temp_file: MagicMock
):

    MagicMock(Task)

    file_info1 = MagicMock(FileInfo)
    type(file_info1).filename = "file1.txt"
    type(file_info1).variable = "file1"

    mocked_target_path1 = MagicMock(Path)

    mocked_temp_file_in_dir.return_value = mocked_target_path1

    variable_fetcher = AsyncMock()

    async with Context(
        variable_fetcher=variable_fetcher,
        message_correlator=AsyncMock(),
        signal_emitter=AsyncMock(),
    ) as ctx:
        assert mocked_target_path1 == await ctx.download_file(file_info1)

    # Assert
    variable_fetcher.assert_awaited_once_with(
        variable_name="file1", file_path=str(mocked_target_path1)
    )
    mocked_temp_file_in_dir.assert_called_once_with("file1.txt", Delete.ALWAYS)
    mocked_temp_file.assert_not_called()


@mock.patch("fastbpmn.context.context.Context.temp_file")
@mock.patch("fastbpmn.context.context.Context.temp_file_in_dir")
@pytest.mark.asyncio
async def test_download_file_without_name(
    mocked_temp_file_in_dir: MagicMock, mocked_temp_file: MagicMock
):

    MagicMock(Task)

    file_info2 = MagicMock(FileInfo)
    type(file_info2).filename = None
    type(file_info2).variable = "file2"

    mocked_target_path2 = MagicMock(Path)

    mocked_temp_file.return_value = mocked_target_path2
    variable_fetcher = AsyncMock()

    async with Context(
        variable_fetcher=variable_fetcher,
        message_correlator=AsyncMock(),
        signal_emitter=AsyncMock(),
    ) as ctx:
        assert mocked_target_path2 == await ctx.download_file(file_info2)

    # Assert
    variable_fetcher.assert_awaited_once_with(
        variable_name="file2", file_path=str(mocked_target_path2)
    )
    mocked_temp_file_in_dir.assert_not_called()
    mocked_temp_file.assert_called_once_with(Delete.ALWAYS)


@mock.patch("fastbpmn.context.context.Context.temp_file")
@mock.patch("fastbpmn.context.context.Context.temp_file_in_dir")
@pytest.mark.asyncio
async def test_download_file_variable_fetch_error(
    mocked_temp_file_in_dir: MagicMock, mocked_temp_file: MagicMock
):

    MagicMock(Task)

    file_info = MagicMock(FileInfo)
    type(file_info).filename = "test.txt"
    type(file_info).variable = "test_var"

    mocked_target_path = MagicMock(Path)
    mocked_temp_file_in_dir.return_value = mocked_target_path

    variable_fetcher = AsyncMock()
    variable_fetcher.side_effect = VariableFetchError(
        "fetch failed", variable_name="test_var", file_path="/tmp/test.txt"
    )

    async with Context(
        variable_fetcher=variable_fetcher,
        message_correlator=AsyncMock(),
        signal_emitter=AsyncMock(),
    ) as ctx:
        with pytest.raises(VariableFetchError, match="fetch failed"):
            await ctx.download_file(file_info)


@mock.patch("fastbpmn.context.context.delete_all")
@pytest.mark.asyncio
async def test_emit_signal_success(patched_delete_all):
    signal_emitter = AsyncMock()
    signal_emitter.return_value = SignalResult(success=True)

    async with Context(
        variable_fetcher=AsyncMock(),
        message_correlator=AsyncMock(),
        signal_emitter=signal_emitter,
    ) as ctx:
        result = await ctx.emit_signal(Signal(signal_name="test-signal"))

    assert result is None
    signal_emitter.assert_awaited_once()
    patched_delete_all.assert_awaited_once()


@mock.patch("fastbpmn.context.context.delete_all")
@pytest.mark.asyncio
async def test_emit_signal_failure(patched_delete_all):
    signal_emitter = AsyncMock()
    signal_emitter.return_value = SignalResult(success=False, error_message="fail")

    async with Context(
        variable_fetcher=AsyncMock(),
        message_correlator=AsyncMock(),
        signal_emitter=signal_emitter,
    ) as ctx:
        with pytest.raises(SignalFailureError, match="fail"):
            await ctx.emit_signal(Signal(signal_name="test-signal"))

    signal_emitter.assert_awaited_once()
    patched_delete_all.assert_awaited_once()


@mock.patch("fastbpmn.context.context.delete_all")
@pytest.mark.asyncio
async def test_correlate_message_success(patched_delete_all):
    message_correlator = AsyncMock()
    expected_result = MessageResult(recipients=[])
    message_correlator.return_value = expected_result

    async with Context(
        variable_fetcher=AsyncMock(),
        message_correlator=message_correlator,
        signal_emitter=AsyncMock(),
    ) as ctx:
        result = await ctx.correlate_message(Message(message_name="test-message"))

    assert result == expected_result
    message_correlator.assert_awaited_once()
    patched_delete_all.assert_awaited_once()


@mock.patch("fastbpmn.context.context.delete_all")
@pytest.mark.asyncio
async def test_correlate_message_failure(patched_delete_all):
    message_correlator = AsyncMock()
    message_correlator.return_value = MessageFailure(error_message="nope")

    async with Context(
        variable_fetcher=AsyncMock(),
        message_correlator=message_correlator,
        signal_emitter=AsyncMock(),
    ) as ctx:
        with pytest.raises(MessageCorrelateError, match="nope"):
            await ctx.correlate_message(Message(message_name="test-message"))

    message_correlator.assert_awaited_once()
    patched_delete_all.assert_awaited_once()
