from enum import Flag, auto
from pathlib import Path


class Delete(Flag):
    NEVER = 0
    ON_SUCCESS = auto()
    ON_FAILURE = auto()
    ALWAYS = ON_SUCCESS | ON_FAILURE


class TempPath:
    def __init__(self, path: Path, delete_flags: Delete = Delete.ALWAYS) -> None:
        super().__init__()
        self.path = path
        self.delete_flags = delete_flags

    def to_be_deleted(self, error: bool) -> bool:

        if not error and self.delete_flags & Delete.ON_SUCCESS:
            return True
        if error and self.delete_flags & Delete.ON_FAILURE:
            return True

        return False

    @property
    def is_dir(self) -> bool:
        return self.path.is_dir()

    @property
    def is_file(self) -> bool:
        return self.path.is_file()
