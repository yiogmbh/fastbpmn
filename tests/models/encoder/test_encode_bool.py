import pytest

from yio_minions.models.encoder import camunda_encode_bool


@pytest.mark.parametrize(
    "value",
    [pytest.param(True, id="True Value"), pytest.param(False, id="False Value")],
)
def test_encode_bool(value: bool):

    encoded = camunda_encode_bool(value)

    assert encoded == {"value": value, "type": "Boolean", "valueInfo": {}}
