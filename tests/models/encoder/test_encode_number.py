from decimal import Decimal

import pytest

from yio_minions.models.encoder import (
    camunda_encode_decimal,
    camunda_encode_long,
    camunda_encode_number,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(Decimal(0), "0", id="Zero"),
        pytest.param(Decimal("1.333"), "1.333", id="Number to be quantized"),
        pytest.param(Decimal("-1.999"), "-1.999", id="Neg. Number to be quantized"),
    ],
)
def test_encode_number_decimal(value: Decimal, expected: Decimal):

    encoded = camunda_encode_decimal(value)

    assert encoded == {"value": expected, "type": "String", "valueInfo": {}}


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(0, 0.0, id="Zero"),
        pytest.param(1, 1.0, id="Number to be quantized"),
        pytest.param(-1, -1.0, id="Neg. Number to be quantized"),
    ],
)
def test_encode_float(value: float, expected: float):

    encoded = camunda_encode_number(value)

    assert encoded == {"value": expected, "type": "Double", "valueInfo": {}}


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(0, 0, id="Zero"),
        pytest.param(1, 1, id="Number to be quantized"),
        pytest.param(-1, -1, id="Neg. Number to be quantized"),
    ],
)
def test_encode_long(value: int, expected):

    encoded = camunda_encode_long(value)

    assert encoded == {"value": expected, "type": "Long", "valueInfo": {}}
