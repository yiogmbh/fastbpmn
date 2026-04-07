from typing import List

import pytest

from fastbpmn.models.encoder import camunda_encode_iterable


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(["a", "b"], ['["a", "b"]'], id="lst_a"),
        pytest.param({"a", "b"}, ['["b", "a"]', '["a", "b"]'], id="set_b"),
    ],
)
def test_camunda_encode_iterable(value: List, expected: str):

    encoded = camunda_encode_iterable(value)

    assert encoded in [
        {"value": expected, "type": "Json", "valueInfo": {}} for expected in expected
    ]
