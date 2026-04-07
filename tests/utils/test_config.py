import pytest
from pydantic import HttpUrl, TypeAdapter
from pydantic_core import Url

from fastbpmn.utils.config import ProtectedUrl, check_password, check_username


@pytest.fixture
def input_url(request):
    return HttpUrl(request.param)


@pytest.mark.parametrize(
    "input_url, expects_error",
    [
        pytest.param("http://localhost", True, id="no username/password"),
        pytest.param("http://user@localhost", True, id="no password"),
        pytest.param("http://user:password@localhost", False, id="username/password"),
        pytest.param(
            "http://user:password@localhost:8080", False, id="username/password/port"
        ),
    ],
    indirect=["input_url"],
)
def test_protected_url(input_url: Url, expects_error: bool):
    """
    Verifies that the protected Url definition works as expected
    """
    adapter = TypeAdapter(ProtectedUrl)

    if expects_error:
        with pytest.raises(ValueError):
            check_username(input_url)
            check_password(input_url)

        with pytest.raises(ValueError):
            adapter.validate_python(input_url)

    else:
        assert check_username(input_url) is not None
        assert check_password(input_url) is not None
        assert adapter.validate_python(input_url) is not None
