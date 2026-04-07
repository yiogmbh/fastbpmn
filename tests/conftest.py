from contextlib import contextmanager

import pytest


@contextmanager
def raise_or_not(error_type):
    if error_type is not None:
        with pytest.raises(error_type) as exc:
            yield exc
    else:
        yield


@pytest.fixture()
def error_expectation(request):

    _error_type = request.param

    # return error_context_manager(error_type)
    raise NotImplementedError("Fixture not yet implemented")
