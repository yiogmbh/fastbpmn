from contextlib import nullcontext as does_not_raise
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest

from yio_minions.context.context import Context
from yio_minions.context.io import Delete, TempPath
from yio_minions.models import FileInfo
from yio_minions.task import Task


class UnitTestError(Exception):
    """
    Some error defined for unit test usage
    """


@mock.patch("yio_minions.context.context.delete_all")
@pytest.mark.asyncio
async def test_context_manager_no_op(patched_delete_all):
    async with Context(file_downloader=MagicMock()):
        pass

    patched_delete_all.assert_awaited_once_with(temp_paths=[], error=False)


@pytest.mark.parametrize(
    "error,expectation",
    [
        pytest.param(False, does_not_raise(), id="no error"),
        pytest.param(True, pytest.raises(UnitTestError), id="error"),
    ],
)
@mock.patch("yio_minions.context.context.create_temp_file")
@mock.patch("yio_minions.context.context.create_temp_dir")
@mock.patch("yio_minions.context.context.delete_all")
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
        async with Context(file_downloader=MagicMock()) as ctx:
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


@mock.patch("yio_minions.context.context.Context.temp_file")
@mock.patch("yio_minions.context.context.Context.temp_file_in_dir")
@pytest.mark.asyncio
async def test_download_file_with_name(
    mocked_temp_file_in_dir: MagicMock, mocked_temp_file: MagicMock
):

    MagicMock(Task)

    file_info1 = MagicMock(FileInfo)
    type(file_info1).filename = "file1.txt"
    type(file_info1).variable = "file1"

    mocked_target_path1 = MagicMock(Path)

    mocked_contents1 = MagicMock(bytes)

    mocked_temp_file_in_dir.return_value = mocked_target_path1

    mocked_file_downloader = AsyncMock()
    mocked_file_downloader.return_value = mocked_contents1

    async with Context(mocked_file_downloader) as ctx:
        assert mocked_target_path1 == await ctx.download_file(file_info1)

    # Assert
    mocked_file_downloader.assert_awaited_once_with("file1")
    mocked_target_path1.write_bytes.assert_called_once_with(mocked_contents1)
    mocked_temp_file_in_dir.assert_called_once_with("file1.txt", Delete.ALWAYS)
    mocked_temp_file.assert_not_called()


@mock.patch("yio_minions.context.context.Context.temp_file")
@mock.patch("yio_minions.context.context.Context.temp_file_in_dir")
@pytest.mark.asyncio
async def test_download_file_without_name(
    mocked_temp_file_in_dir: MagicMock, mocked_temp_file: MagicMock
):

    MagicMock(Task)

    file_info2 = MagicMock(FileInfo)
    type(file_info2).filename = None
    type(file_info2).variable = "file2"

    mocked_target_path2 = MagicMock(Path)

    mocked_contents2 = MagicMock(bytes)

    mocked_temp_file.return_value = mocked_target_path2
    mocked_file_downloader = AsyncMock()
    mocked_file_downloader.return_value = mocked_contents2

    async with Context(mocked_file_downloader) as ctx:
        assert mocked_target_path2 == await ctx.download_file(file_info2)

    # Assert
    mocked_file_downloader.assert_awaited_once_with("file2")
    mocked_target_path2.write_bytes.assert_called_once_with(mocked_contents2)
    mocked_temp_file_in_dir.assert_not_called()
    mocked_temp_file.assert_called_once_with(Delete.ALWAYS)
