from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPISendCallable,
    ExternalTaskScope,
)
from typing import cast
from opentelemetry.metrics import Meter
from opentelemetry.trace import Tracer

from .metrics import LifespanMetrics
from .metrics import MetricsMiddleware
from .lifespan import track_lifespan
from .lifespan import wrap_lifespan
from .tracing import TracingMiddleware

__all__ = (
    "LifespanMetrics",
    "MetricsMiddleware",
    "ObservabilityMiddleware",
    "track_lifespan",
    "TracingMiddleware",
    "wrap_lifespan",
)


class ObservabilityMiddleware:
    """Enable tracing and metrics together with tracing as the outer layer."""

    def __init__(
        self,
        app: AETPIApplication,
        *,
        tracer: Tracer | None = None,
        meter: Meter | None = None,
        include_tenant: bool = False,
        include_business_key: bool = False,
        record_exception_details: bool = True,
        record_variable_details: bool = False,
    ) -> None:
        metrics_middleware = MetricsMiddleware(
            app,
            meter=meter,
            include_tenant=include_tenant,
        )
        self.app = TracingMiddleware(
            cast(
                AETPIApplication,
                metrics_middleware,
            ),
            tracer=tracer,
            include_tenant=include_tenant,
            include_business_key=include_business_key,
            record_exception_details=record_exception_details,
            record_variable_details=record_variable_details,
        )

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        await self.app(scope, receive, send)
