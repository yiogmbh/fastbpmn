import functools
from contextlib import asynccontextmanager, AbstractContextManager
from typing import Callable, ParamSpec, TypeVar, AsyncGenerator

import anyio.to_thread
from anyio import CapacityLimiter
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


@asynccontextmanager
async def contextmanager_in_threadpool(
    cm: AbstractContextManager[T],
) -> AsyncGenerator[T, None]:
    # blocking __exit__ from running waiting on a free thread
    # can create race conditions/deadlocks if the context manager itself
    # has its own internal pool (e.g. a database connection pool)
    # to avoid this we let __exit__ run without a capacity limit
    # since we're creating a new limiter for each call, any non-zero limit
    # works (1 is arbitrary)
    exit_limiter = CapacityLimiter(1)
    try:
        yield await run_in_threadpool(cm.__enter__)
    except Exception as e:
        ok = bool(
            await anyio.to_thread.run_sync(
                wrap_log_context(cm.__exit__),
                type(e),
                e,
                e.__traceback__,
                limiter=exit_limiter,
            )
        )
        if not ok:
            raise e
    else:
        await anyio.to_thread.run_sync(
            wrap_log_context(cm.__exit__), None, None, None, limiter=exit_limiter
        )
