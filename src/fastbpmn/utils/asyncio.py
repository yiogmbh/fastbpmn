import asyncio
from asyncio import Semaphore, Lock
from functools import wraps
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")


async def cancel_and_wait(coro) -> None:
    """
    Cancel a coroutine and wait for it to finish.
    """
    try:
        coro.cancel()
        await coro
    except asyncio.CancelledError:
        pass


# 2. Type the outer factory function
def lock_decorator() -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]
]:
    lock = Lock()

    # 3. Type the decorator itself
    def decorator(
        coro: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(coro)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            async with lock:
                return await coro(*args, **kwargs)

        return wrapper

    return decorator


def semaphore(n: int) -> Callable[..., Callable[..., Coroutine[Any, Any, Any]]]:
    def decorator(coro: Coroutine) -> Callable[..., Coroutine[Any, Any, Any]]:
        lock = Semaphore(n)

        @wraps(coro)
        async def wrapper(*args, **kwargs):

            async with lock:
                return await coro(*args, **kwargs)

        return wrapper

    return decorator
