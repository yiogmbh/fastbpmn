import base64
import mimetypes
from pathlib import Path
from typing import Any, TypedDict

import magic
from pydantic import TypeAdapter

json_type_adapter = TypeAdapter(dict | list | tuple | set)


class Camunda7FileValueInfo(TypedDict, total=False):
    filename: str
    mimetype: str
    encoding: str


class CamundaTypeDict(TypedDict, total=False):
    value: Any
    type: str
    valueInfo: Camunda7FileValueInfo


def as_base64(value: Path) -> str:
    """
    Transform the given file (path object) into a base64 string.
    """
    return base64.b64encode(value.read_bytes()).decode("utf-8")


def determine_mime(value: Path) -> str | None:
    """
    Try to detect the mime type using a multi staged approach
    """
    try:
        return magic.from_file(value, mime=True)
    except magic.MagicException:
        pass

    # Try based on file suffix only
    mime, _ = mimetypes.guess_type(value)

    return mime


def to_file(value: Path) -> CamundaTypeDict:
    """
    Converts the given value to a file
    """
    value_info = {"filename": value.name, "encoding": "utf-8"}

    if (mime_type := determine_mime(value)) is not None:
        value_info["mimetype"] = mime_type

    return {"value": as_base64(value), "type": "File", "valueInfo": value_info}


def to_null(value: None = None) -> CamundaTypeDict:
    """
    Converts the given value to a string
    """
    return {"value": value, "type": "Null"}


def to_bool(value: bool) -> CamundaTypeDict:
    """
    Converts the given value to a boolean
    """
    return {"value": value, "type": "Boolean"}


def to_long(value: int) -> CamundaTypeDict:
    """
    Converts the given value to a long
    """
    return {"value": value, "type": "Long"}


def to_double(value: float) -> CamundaTypeDict:
    """
    Converts the given value to a double
    """
    return {"value": value, "type": "Double"}


def to_string(value: str) -> CamundaTypeDict:
    """
    Converts the given value to a string
    """
    return {"value": value, "type": "String"}


def to_json(value: dict | list | tuple | set) -> CamundaTypeDict:
    """
    Converts the given value to a json string
    """
    return {"value": json_type_adapter.dump_json(value).decode("utf-8"), "type": "Json"}


def encode_variable(value: Any) -> dict[str, Any]:
    """
    Encodes a single variable to be used with camunda rest api
    """
    match value:
        case None:
            return to_null(value)
        case bool():
            return to_bool(value)
        case int():
            return to_long(value)
        case float():
            return to_double(value)
        case str():
            return to_string(value)
        case dict() | list() | tuple() | set():
            return to_json(value)
        case Path():
            return to_file(value)

    raise ValueError(f"Unsupported value type: {type(value)}")


def encode_variables(variables: dict[str, Any]) -> dict[str, Any]:
    """
    Encode the given input variables to be used with camunda rest api

    For some values that requires special handling, to encode them properly
    """
    return {key: encode_variable(value) for key, value in variables.items()}
