from fastbpmn.models.encoder import camunda_dumps_variables, camunda_encode_bytes


def test_encode_bytes():
    result = camunda_encode_bytes(b"Hello World")
    assert result == {
        "value": "SGVsbG8gV29ybGQ=",
        "type": "Bytes",
        "valueInfo": {},
    }


def test_encode_empty_bytes():
    result = camunda_encode_bytes(b"")
    assert result == {
        "value": "",
        "type": "Bytes",
        "valueInfo": {},
    }


def test_camunda_dumps_variables_with_bytes():
    variables = {"name": "test", "data": b"some bytes"}
    result = camunda_dumps_variables(variables)
    assert result["name"] == {"type": "String", "value": "test", "valueInfo": {}}
    assert result["data"]["type"] == "Bytes"
    assert result["data"]["value"] == "c29tZSBieXRlcw=="
