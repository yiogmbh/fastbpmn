import json
from typing import Union

from .base import (
    BaseInputModel,
    BaseOutputModel,
    FileInfo,
    InputModel,
    OutputModel,
    get_file_info_indirect,
)
from .decoder import camunda_loads
from .encoder import camunda_dumps_variables
from .task import TaskBPMNError, TaskComplete, TaskFailure


def encode(value: Union[TaskComplete, TaskFailure, TaskBPMNError]) -> str:
    """
    Encodes the given result of an external task into a json string that is compliant with camunda
    :param value: the result as either TaskComplete, TaskFailure or TaskBPMNError
    :return: the resulting json as str.
    """
    value_dict = value.model_dump(by_alias=True, exclude_unset=False, exclude_none=True)

    if "variables" in value_dict:
        value_dict["variables"] = camunda_dumps_variables(value_dict["variables"])

    return json.dumps(value_dict)


__all__ = [
    "BaseInputModel",
    "BaseOutputModel",
    "InputModel",
    "OutputModel",
    "TaskComplete",
    "TaskFailure",
    "TaskBPMNError",
    "camunda_loads",
    "encode",
    "FileInfo",
    "get_file_info_indirect",
]
