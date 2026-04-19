from pathlib import Path as PyPath
from typing import Annotated, Any, Callable, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainValidator


class InputOutputModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


BaseInputModel = InputOutputModel
BaseOutputModel = InputOutputModel

InputModel = TypeVar("InputModel", bound=BaseInputModel)
OutputModel = TypeVar("OutputModel", bound=BaseOutputModel)


def to_path(value: Any, handler) -> PyPath:

    if isinstance(value, PyPath):
        return value
    if isinstance(value, FileInfo):
        try:
            return value.sync_download()
        except Exception as e:
            raise ValueError(
                f"Unable to download file (filename<{value.filename}>)"
            ) from e
    return handler(value)


Path = Annotated[PyPath, PlainValidator(to_path)]


class FileInfo(BaseModel):
    """
    Handling for file values

    **Remark** Already uses PydanticV2.
    """

    filename: str | None = Field(None, alias="filename")
    mimetype: str | None = Field(None, alias="mimetype")
    encoding: str | None = Field(None, alias="encoding")
    variable: str | None = Field(None, alias="variable_name")

    sync_download: Callable[[], Path] | None = Field(
        None, exclude=True, alias="sync_download"
    )


def get_file_info_indirect(
    instance: BaseInputModel, indirect_key: str, required: bool = True
) -> FileInfo:
    """
    Use this method in a cached/computed property to get access to FileInfo objects in an indirect way.

    That means, using the given "indirect_key" the method will lookup the variable name of the actual
    file info object and return it.
    """
    file_info = getattr(instance, indirect_key, None)

    if file_info is None and required:
        raise ValueError(
            f"Var: {indirect_key} is empty/None/not existing (indirect lookup)"
        )

    if file_info and not isinstance(file_info, FileInfo):
        raise ValueError(f"Var: {indirect_key} is not a FileInfo (indirect lookup)")

    return file_info
