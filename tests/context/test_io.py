from pathlib import Path
from unittest.mock import MagicMock

import pytest

from yio_minions.context.io import Delete, TempPath


@pytest.mark.parametrize(
    "error,flags",
    [
        pytest.param(False, Delete.ALWAYS, id="delete: No Error (always)"),
        pytest.param(True, Delete.ALWAYS, id="delete: Error (always)"),
        pytest.param(False, Delete.ON_SUCCESS, id="delete: No Error (on success)"),
        pytest.param(True, Delete.ON_FAILURE, id="delete: Error (on failure)"),
    ],
)
def test_to_be_deleted(error: bool, flags: Delete):

    mocked_path = MagicMock(Path)
    temp_path = TempPath(path=mocked_path, delete_flags=flags)

    assert temp_path.to_be_deleted(error) is True


@pytest.mark.parametrize(
    "error,flags",
    [
        pytest.param(False, Delete.NEVER, id="Don't delete: No Error (Never)"),
        pytest.param(True, Delete.NEVER, id="Don't delete: Error (Never)"),
        pytest.param(
            False, Delete.ON_FAILURE, id="Don't delete: No Error (on failure)"
        ),
        pytest.param(True, Delete.ON_SUCCESS, id="Don't delete: Error (on success)"),
    ],
)
def test_not_to_be_deleted(error: bool, flags: Delete):

    mocked_path = MagicMock(Path)
    temp_path = TempPath(path=mocked_path, delete_flags=flags)

    assert temp_path.to_be_deleted(error) is False


def test_delete_flag():
    assert Delete.ON_SUCCESS | Delete.ON_FAILURE == Delete.ALWAYS
    assert Delete.ON_SUCCESS & Delete.ON_FAILURE == Delete.NEVER
    assert Delete.ALWAYS & Delete.ON_FAILURE == Delete.ON_FAILURE
    assert Delete.ALWAYS & Delete.ON_SUCCESS == Delete.ON_SUCCESS

    for flag in Delete:
        assert Delete.NEVER & flag == Delete.NEVER
