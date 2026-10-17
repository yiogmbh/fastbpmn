from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPISendCallable,
    ExternalTaskScope,
)
from typing import cast
from opentelemetry.metrics import Meter
from opentelemetry.trace import Tracer

from .metrics import MetricsMiddleware
from .tracing import TracingMiddleware

__all__ = ("ObservabilityMiddleware",)


class ObservabilityMiddleware:
    """Enable tracing and metrics together with tracing as the outer layer."""

    def __init__(
        self,
        app: AETPIApplication,
        *,
        tracer: Tracer | None = None,
        meter: Meter | None = None,
        include_tenant: bool = False,
        record_exception_details: bool = True,
    ) -> None:
        self.app = TracingMiddleware(
            cast(
                AETPIApplication,
                MetricsMiddleware(
                    app,
                    meter=meter,
                    include_tenant=include_tenant,
                ),
            ),
            tracer=tracer,
            include_tenant=include_tenant,
            record_exception_details=record_exception_details,
        )

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        await self.app(scope, receive, send)
