import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path

from yio_minions.models.encoder import (
    camunda_encode_dict,
    camunda_encode_model_v1,
    camunda_encode_model_v2,
)


def test_pydantic_v1():
    """
    Verifies that the pydantic v1 models get dumped as expected
    """
    from pydantic.v1 import BaseModel, Field

    class Model(BaseModel):
        a: int
        b: str = Field(..., alias="b_alias")

    model = Model(a=1, b_alias="test")

    encoded = camunda_encode_model_v1(model)

    # assert
    assert encoded == {
        "value": '{"a": 1, "b_alias": "test"}',
        "type": "Json",
        "valueInfo": {},
    }


def test_pydantic_v2():
    """
    Verifies that pydantic v2 models get dumped as expected
    """
    from pydantic import BaseModel, Field

    class Model(BaseModel):
        a: int
        b: str = Field(..., alias="b_alias")

    model = Model(a=1, b_alias="test")
    encoded = camunda_encode_model_v2(model)

    # assert
    assert encoded == {
        "value": '{"a":1,"b_alias":"test"}',
        "type": "Json",
        "valueInfo": {},
    }


def test_encode_dict():
    """
    Verifies that dicts get dumped as expected
    """
    encoded = camunda_encode_dict({"a": 1, "b_alias": "test"})

    # assert
    assert encoded == {
        "value": '{"a": 1, "b_alias": "test"}',
        "type": "Json",
        "valueInfo": {},
    }


def test_encode_dict_with_model_v2():
    """
    Verifies that dicts with pydantic models get dumped as expected
    """
    from pydantic import BaseModel, Field

    class Model(BaseModel):
        a: int
        b: str = Field(..., alias="b_alias")

    model = Model(a=1, b_alias="test")

    encoded = camunda_encode_dict({"a": 1, "b_alias": "test", "model": model})

    # assert
    assert encoded == {
        "value": '{"a": 1, "b_alias": "test", "model": {"a": 1, "b_alias": "test"}}',
        "type": "Json",
        "valueInfo": {},
    }


def test_encode_dict_with_model_v1():
    """
    Verifies that dicts with pydantic models get dumped as expected
    """
    from pydantic.v1 import BaseModel, Field

    class Model(BaseModel):
        a: int
        b: str = Field(..., alias="b_alias")

    model = Model(a=1, b_alias="test")

    encoded = camunda_encode_dict({"a": 1, "b_alias": "test", "model": model})

    # assert
    assert encoded == {
        "value": '{"a": 1, "b_alias": "test", "model": {"a": 1, "b_alias": "test"}}',
        "type": "Json",
        "valueInfo": {},
    }


def test_encode_dict_with_special_values():
    """
    Tests if a dict with special values gets dumped as expected

    - datetime
    - date
    - decimal
    - enum
    - uuid
    - set
    """

    class TestEnum(Enum):
        A = 0

    encoded = camunda_encode_dict(
        {
            "date": date(2020, 1, 1),
            "datetime": datetime(2020, 1, 1),
            "decimal": Decimal("1.123"),
            "enum": TestEnum.A,
            "uuid": uuid.UUID("12345678-1234-5678-1234-567812345678"),
            "set": {"a", "b"},
            "string": "Hello World",
            "path": Path("/not/existing/path"),
        }
    )

    # assert
    assert encoded["type"] == "Json"
    assert encoded["valueInfo"] == {}
    assert any(
        (
            json.loads(encoded["value"])
            == json.loads(
                '{"date": "2020-01-01", "datetime": "2020-01-01T00:00:00", "decimal": "1.123", "enum": 0, "uuid": "12345678-1234-5678-1234-567812345678", "set": ["a", "b"], "string": "Hello World", "path": "/not/existing/path"}'
            ),
            json.loads(encoded["value"])
            == json.loads(
                '{"date": "2020-01-01", "datetime": "2020-01-01T00:00:00", "decimal": "1.123", "enum": 0, "uuid": "12345678-1234-5678-1234-567812345678", "set": ["b", "a"], "string": "Hello World", "path": "/not/existing/path"}'
            ),
        )
    )
