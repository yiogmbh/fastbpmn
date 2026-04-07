from datetime import date

import pytest

from yio_minions.models.encoder import camunda_encode_date


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(date.today(), date.today().isoformat(), id="today"),
    ],
)
def test_encode_number_decimal(value: date, expected: str):

    encoded = camunda_encode_date(value)

    assert encoded == {"value": expected, "type": "String", "valueInfo": {}}
