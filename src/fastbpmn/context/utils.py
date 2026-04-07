import shutil
import tempfile
from pathlib import Path
from typing import List

from .io import Delete, TempPath


def create_temp_file(flags: Delete, suffix: str = None) -> TempPath:
    _, temporary_file = tempfile.mkstemp(suffix=suffix)

    return TempPath(path=Path(temporary_file), delete_flags=flags)


def create_temp_dir(flags: Delete) -> TempPath:
    temporary_directory = tempfile.mkdtemp()

    return TempPath(path=Path(temporary_directory), delete_flags=flags)


async def delete_all(temp_paths: List[TempPath], error: bool) -> None:
    # pylint: disable=expression-not-assigned
    [delete(temp_path) for temp_path in temp_paths if temp_path.to_be_deleted(error)]


def delete(temp_path: TempPath) -> None:

    if temp_path.is_dir:
        shutil.rmtree(temp_path.path, ignore_errors=False, onerror=None)

    if temp_path.is_file:
        temp_path.path.unlink()
