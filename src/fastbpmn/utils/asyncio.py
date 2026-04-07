import asyncio
from asyncio import Semaphore
from functools import wraps
from typing import Any, Callable, Coroutine


async def cancel_and_wait(coro) -> None:
    """
    Cancel a coroutine and wait for it to finish.
    """
    try:
        coro.cancel()
        await coro
    except asyncio.CancelledError:
        pass


def semaphore(n: int) -> Callable[..., Callable[..., Coroutine[Any, Any, Any]]]:
    def decorator(coro: Coroutine) -> Callable[..., Coroutine[Any, Any, Any]]:
        lock = Semaphore(n)

        @wraps(coro)
        async def wrapper(*args, **kwargs):

            async with lock:
                return await coro(*args, **kwargs)

        return wrapper

    return decorator
