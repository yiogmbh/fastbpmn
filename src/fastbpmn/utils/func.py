import functools


def call_once_only(func):
    """
    Decorator to ensure that the decorated function can be called only once.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if wrapper.called:
            return wrapper.return_value

        wrapper.called = True
        wrapper.return_value = func(*args, **kwargs)

        return wrapper.return_value

    wrapper.called = False
    wrapper.return_value = None

    return wrapper
