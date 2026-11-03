from __future__ import annotations

import contextlib
import warnings
from collections.abc import Callable
from typing import Any

from .metrics import LifespanMetrics

__all__ = ("track_lifespan", "wrap_lifespan")


def wrap_lifespan(
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


def track_lifespan(meter: Any | None = None) -> Any:
    """Deprecated alias for :func:`wrap_lifespan`."""
    warnings.warn(
        "track_lifespan is deprecated; use wrap_lifespan instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return wrap_lifespan(meter)
