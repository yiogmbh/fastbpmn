import functools
from typing import Callable, ParamSpec, TypeVar

import anyio.to_thread
import structlog

P = ParamSpec("P")
T = TypeVar("T")


async def run_in_threadpool(
    func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    """
    Runs a function in a separate threadpool to stay asynchronous within our application

    **Remark**: The method tries to ensure that the logging context is preserved when offloading work to a thread.

    :param func: The function to run
    :param args: Arguments to pass to the function
    :param kwargs: Keyword arguments to pass to the function

    """
    func = functools.partial(wrap_log_context(func), *args, **kwargs)
    return await anyio.to_thread.run_sync(func)


def wrap_log_context(func: Callable[P, T]) -> Callable[P, T]:

    ctx = structlog.contextvars.get_contextvars()

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Callable[P, T]:
        structlog.contextvars.bind_contextvars(**ctx)

        return func(*args, **kwargs)

    return wrapper
