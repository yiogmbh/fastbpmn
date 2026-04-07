import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from unittest.mock import patch

import pytest

from yio_minions.errors import DatatypeNotSupported
from yio_minions.models import camunda_dumps_variables


@patch("yio_minions.models.encoder.camunda_encode_file")
def test_camunda_dumps_variables(mocked_encode_file):
    """
    Test a whole bunch of cases for camunda_dumps_variables at once by providing
    a dict with a lot of different types.

    - bool
    - float
    - int
    - decimal
    - str
    - uuid
    - date
    - datetime
    - enum
    - path
    - dict
    - list
    - set
    - pydantic models v1/v2
    """

    # make sure to mock camunda_encode_file, so that we don't have to deal with files and existance here
    mocked_encode_file.return_value = {
        "value": "SGFsbG8K",
        "type": "File",
        "valueInfo": {
            "filename": "test.txt",
            "mimetype": "text/plain",
            "encoding": "utf-8",
        },
    }

    from pydantic import BaseModel, Field
    from pydantic.v1 import BaseModel as BaseModelV1
    from pydantic.v1 import Field as FieldV1

    class ModelV1(BaseModelV1):
        a: int
        b: str = FieldV1(..., alias="b_alias")

    class ModelV2(BaseModel):
        a: int
        b: str = Field(..., alias="b_alias")

    class TestEnum(Enum):
        A = 0
        B = "test"

    variables = {
        "bool": True,
        "float": 1.82,
        "int": 1,
        "decimal": Decimal("1.82"),
        "str": "test",
        "uuid": uuid.UUID("00000000-0000-0000-0000-000000000000"),
        "date": date.fromisoformat("2021-01-01"),
        "datetime": datetime.fromisoformat("2021-01-01T00:00:00+00:00"),
        "enum": TestEnum.A,
        "strenum": TestEnum.B,
        "path": Path("/not/existing/path"),
        "dict": {"a": 1},
        "list": [1, 2, 3],
        "set": {"a", "b"},
        "model_v1": ModelV1(a=1, b_alias="test"),
        "model_v2": ModelV2(a=1, b_alias="test"),
    }

    encoded = camunda_dumps_variables(variables)

    assert "bool" in encoded
    assert encoded["bool"] == {"value": True, "type": "Boolean", "valueInfo": {}}
    assert "float" in encoded
    assert encoded["float"] == {"value": 1.82, "type": "Double", "valueInfo": {}}
    assert "int" in encoded
    assert encoded["int"] == {"value": 1, "type": "Long", "valueInfo": {}}
    assert "decimal" in encoded
    assert encoded["decimal"] == {"value": "1.82", "type": "String", "valueInfo": {}}
    assert "str" in encoded
    assert encoded["str"] == {"value": "test", "type": "String", "valueInfo": {}}
    assert "uuid" in encoded
    assert encoded["uuid"] == {
        "value": "00000000-0000-0000-0000-000000000000",
        "type": "String",
        "valueInfo": {},
    }
    assert "date" in encoded
    assert encoded["date"] == {"value": "2021-01-01", "type": "String", "valueInfo": {}}
    assert "datetime" in encoded
    assert encoded["datetime"] == {
        "value": "2021-01-01T00:00:00+00:00",
        "type": "String",
        "valueInfo": {},
    }
    assert "enum" in encoded
    assert encoded["enum"] == {"value": 0, "type": "Long", "valueInfo": {}}
    assert "strenum" in encoded
    assert encoded["strenum"] == {"value": "test", "type": "String", "valueInfo": {}}
    assert "path" in encoded
    assert encoded["path"] == {
        "value": "SGFsbG8K",
        "type": "File",
        "valueInfo": {
            "filename": "test.txt",
            "mimetype": "text/plain",
            "encoding": "utf-8",
        },
    }
    assert "dict" in encoded
    assert encoded["dict"] == {"value": '{"a": 1}', "type": "Json", "valueInfo": {}}
    assert "list" in encoded
    assert encoded["list"] == {"value": "[1, 2, 3]", "type": "Json", "valueInfo": {}}
    assert "set" in encoded
    assert encoded["set"] in [
        {"value": '["a", "b"]', "type": "Json", "valueInfo": {}},
        {"value": '["b", "a"]', "type": "Json", "valueInfo": {}},
    ]
    assert "model_v1" in encoded
    assert encoded["model_v1"] == {
        "value": '{"a": 1, "b_alias": "test"}',
        "type": "Json",
        "valueInfo": {},
    }
    assert "model_v2" in encoded
    assert encoded["model_v2"] == {
        "value": '{"a":1,"b_alias":"test"}',
        "type": "Json",
        "valueInfo": {},
    }


def test_not_supported():
    """
    Tests if a not supported type raises an exception
    """
    with pytest.raises(DatatypeNotSupported) as exc_info:
        camunda_dumps_variables({"test": object()})

    assert "Unsupported DataType of variable test: " in str(exc_info.value)
