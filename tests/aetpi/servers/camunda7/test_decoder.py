from fastbpmn.aetpi.servers.camunda7.decoder import (
    Camunda7Bytes,
    Camunda7TypeAdapter,
    decode_variables,
)


def test_decode_bytes_variable():
    raw = {"my_bytes": {"type": "Bytes", "value": "SGVsbG8gV29ybGQ=", "valueInfo": {}}}
    result = decode_variables(raw)
    assert result == {"my_bytes": b"Hello World"}


def test_decode_bytes_type_adapter():
    result = Camunda7TypeAdapter.validate_python(
        {"name": "x", "type": "Bytes", "value": "Zm9v"}
    )
    assert isinstance(result, Camunda7Bytes)
    assert result.value == b"foo"


def test_decode_bytes_empty_string():
    result = decode_variables(
        {"empty": {"type": "Bytes", "value": "", "valueInfo": {}}}
    )
    assert result == {"empty": b""}


def test_decode_bytes_with_other_variables():
    raw = {
        "name": {"type": "String", "value": "test"},
        "data": {"type": "Bytes", "value": "ZGF0YQ==", "valueInfo": {}},
    }
    result = decode_variables(raw)
    assert result == {"name": "test", "data": b"data"}
