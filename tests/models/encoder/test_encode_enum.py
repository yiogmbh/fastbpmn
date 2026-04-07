from enum import Enum, IntEnum

import pytest

from yio_minions.models.encoder import camunda_encode_enum


class Items(Enum):
    ITEM_A = "item_a"
    ITEM_B = "item_b"


class IntItems(IntEnum):
    ITEM_A = 13
    ITEM_B = 14


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(Items.ITEM_A, "item_a", id="Item is a String"),
    ],
)
def test_encode_enum_str(value: Enum, expected: str):

    encoded = camunda_encode_enum(value)

    assert encoded == {"value": expected, "type": "String", "valueInfo": {}}


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(IntItems.ITEM_A, 13, id="Item is an Integer"),
    ],
)
def test_encode_enum_int(value: IntEnum, expected: int):

    encoded = camunda_encode_enum(value)

    assert encoded == {"value": expected, "type": "Long", "valueInfo": {}}


def test_encode_weird_enum():

    class SomeEnum(Enum):
        ITEM_B = 2.0

    with pytest.raises(ValueError) as exc:
        camunda_encode_enum(SomeEnum.ITEM_B)

    assert "Unable to decode Enum SomeEnum.ITEM_B" in str(exc.value)
