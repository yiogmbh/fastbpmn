import base64
import json
import mimetypes
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, IntEnum
from json import JSONEncoder
from pathlib import Path
from typing import Any, Dict, Optional, Union
from uuid import UUID

import magic
from pydantic import BaseModel as BaseModelV2
from pydantic.v1 import BaseModel as BaseModelV1

from ..errors import DatatypeNotSupported
from .types import CamundaPrimitives


class CamundaEncoder(JSONEncoder):
    # pylint: disable=too-many-return-statements

    # ToDo: ensure proper handling of bool
    def default(self, o: Any) -> Any:

        match o:
            case str():
                result = o
            case Enum():
                result = o.value
            case Decimal() | UUID():
                result = str(o)
            case Path():
                result = o.as_posix()
            case date() | datetime():
                result = o.isoformat()
            case set():
                result = list(o)
            case BaseModelV1():
                # The implementation is less performant than using o.dict but it is more stable
                # as we can ensure json serializability using pydantic internals.
                result = json.loads(o.json(by_alias=True, ensure_ascii=False))
            case BaseModelV2():
                result = o.model_dump(mode="json", by_alias=True)
            case _:
                result = super().default(o)

        return result


def camunda_dumps_variables(variables: Dict[str, Any]):  # noqa: ignore=C901
    """
    This method tries to encode supported datatypes in a way
    that is supported by camunda
    - str
    - float
    - integer
    - bool
    """
    # pylint: disable=too-many-branches

    for key, value in variables.items():
        if isinstance(value, bool):
            variables[key] = camunda_encode_bool(value)
        elif isinstance(value, float):
            variables[key] = camunda_encode_number(value)
        elif isinstance(value, Decimal):
            variables[key] = camunda_encode_str(str(value))
        elif isinstance(value, int):
            variables[key] = camunda_encode_long(value)
        elif isinstance(value, str):
            variables[key] = camunda_encode_str(value)
        elif isinstance(value, uuid.UUID):
            variables[key] = camunda_encode_str(str(value))
        elif isinstance(value, date):
            variables[key] = camunda_encode_date(value)
        elif isinstance(value, Enum):
            variables[key] = camunda_encode_enum(value)
        elif isinstance(value, Path):
            variables[key] = camunda_encode_file(value)
        elif isinstance(value, dict):
            # sufficient to cover the json cases
            variables[key] = camunda_encode_dict(value)
        elif isinstance(
            value,
            (
                list,
                set,
            ),
        ):
            # sufficient to cover the json cases
            variables[key] = camunda_encode_iterable(value)
        elif isinstance(value, BaseModelV1):
            # Probably never reached again ...
            variables[key] = camunda_encode_model_v1(value)
        elif isinstance(value, BaseModelV2):
            variables[key] = camunda_encode_model_v2(value)
        else:
            raise DatatypeNotSupported(
                f"Unsupported DataType of variable {key}: {type(value)}."
            )

    return variables


def camunda_encode_str(value: str) -> dict:
    return camunda_encode_primitive(value, "String")


def camunda_encode_enum(value: Union[Enum, IntEnum]) -> dict:
    if isinstance(value.value, str):
        return camunda_encode_primitive(str(value.value), "String")
    if isinstance(value.value, int):
        return camunda_encode_primitive(int(value.value), "Long")
    raise ValueError(f"Unable to decode Enum {value}")


def camunda_encode_long(value: int) -> dict:
    return camunda_encode_primitive(value, "Long")


def camunda_encode_decimal(value: Decimal) -> dict:
    return camunda_encode_primitive(str(value), "String")


def camunda_encode_number(value: Union[float, Decimal]) -> dict:
    return camunda_encode_primitive(float(Decimal(value)), "Double")


def camunda_encode_bool(value: bool) -> dict:
    return camunda_encode_primitive(value, "Boolean")


def camunda_encode_date(value: date) -> dict:
    return camunda_encode_primitive(value.isoformat(), "String")


def camunda_encode_model_v1(value: BaseModelV1) -> dict:
    return {
        "value": value.json(by_alias=True, ensure_ascii=False),
        "type": "Json",
        "valueInfo": {},
    }


def camunda_encode_model_v2(value: BaseModelV2) -> dict:
    return {
        "value": value.model_dump_json(by_alias=True),
        "type": "Json",
        "valueInfo": {},
    }


def camunda_encode_dict(value: Dict[str, Any]) -> dict:
    return {
        "value": json.dumps(value, ensure_ascii=False, cls=CamundaEncoder),
        "type": "Json",
        "valueInfo": {},
    }


def camunda_encode_iterable(value: Union[set, list]) -> dict:
    """ToDo: ich bin mir da nicht sicher ob das so geht"""
    return {
        "value": json.dumps(value, ensure_ascii=False, cls=CamundaEncoder),
        "type": "Json",
        "valueInfo": {},
    }


def camunda_encode_file(value: Path) -> dict:

    value_info = {"filename": value.name, "encoding": "utf-8"}

    if mime_type := determine_mime(value):
        value_info["mimetype"] = mime_type

    value_result = {"value": as_base64(value), "type": "File", "valueInfo": value_info}
    return value_result


def camunda_encode_primitive(
    value: Any, type_name: str
) -> Dict[str, Union[CamundaPrimitives, Dict[str, str]]]:
    return {"value": value, "type": type_name, "valueInfo": {}}


def as_base64(value: Path) -> str:
    """
    Transform the given file (path object) into a base64 string.
    """
    return base64.b64encode(value.read_bytes()).decode("utf-8")


def determine_mime(value: Path) -> Optional[str]:
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
