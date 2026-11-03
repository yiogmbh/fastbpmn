from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

from .metrics import LifespanMetrics

__all__ = ("track_lifespan",)


def track_lifespan(
    meter: Any | None = None,
) -> Callable[
    [Callable[[Any], contextlib.AbstractAsyncContextManager[Any]]],
    Callable[[Any], contextlib.AbstractAsyncContextManager[Any]],
]:
    """Track lifespan starts and liveness for an async-context lifespan."""
    lifespan_metrics = LifespanMetrics(meter)

    def decorator(
        lifespan: Callable[[Any], contextlib.AbstractAsyncContextManager[Any]],
    ) -> Callable[[Any], contextlib.AbstractAsyncContextManager[Any]]:
        @contextlib.asynccontextmanager
        async def tracked(app: Any) -> Any:
            async with lifespan(app) as state:
                lifespan_metrics.startup()
                try:
                    yield state
                finally:
                    lifespan_metrics.shutdown()

        return tracked

    return decorator
