from fastbpmn.aetpi.servers.camunda7.encoder import encode_variable, encode_variables


def test_encode_bytes():
    result = encode_variable(b"Hello World")
    assert result == {
        "value": "SGVsbG8gV29ybGQ=",
        "type": "Bytes",
        "valueInfo": {},
    }


def test_encode_empty_bytes():
    result = encode_variable(b"")
    assert result == {
        "value": "",
        "type": "Bytes",
        "valueInfo": {},
    }


def test_encode_variables_with_bytes():
    result = encode_variables({"name": "test", "data": b"some bytes"})
    assert result["name"] == {"type": "String", "value": "test"}
    assert result["data"]["type"] == "Bytes"
    assert result["data"]["value"] == "c29tZSBieXRlcw=="
