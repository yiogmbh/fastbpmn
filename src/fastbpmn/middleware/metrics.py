import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from aetpiref.typing import AETPIApplication
from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, Meter, UpDownCounter

from ._observability import (
    EventLifecycleMiddleware,
    OPERATION_REQUESTS,
    OPERATION_RESPONSES,
    TERMINAL_EVENTS,
    event_type,
)

__all__ = ("MetricsMiddleware",)

_INSTRUMENTATION_NAME = "fastbpmn.middleware.metrics"


@dataclass
class _MetricsState:
    attributes: dict[str, str]
    started_at: float | None = None
    active: bool = False
    finished: bool = False
    operations: dict[str, str] = field(default_factory=dict)


class MetricsMiddleware(EventLifecycleMiddleware):
    """Collect OpenTelemetry metrics for external-task processing."""

    def __init__(
        self,
        app: AETPIApplication,
        *,
        meter: Meter | None = None,
        include_tenant: bool = False,
    ) -> None:
        super().__init__(app, include_tenant=include_tenant)
        self.meter = meter or metrics.get_meter(_INSTRUMENTATION_NAME)
        self.executions: Counter = self.meter.create_counter(
            "fastbpmn.external_task.executions",
            unit="{execution}",
            description="External-task executions by outcome.",
        )
        self.execution_duration: Histogram = self.meter.create_histogram(
            "fastbpmn.external_task.execution_duration",
            unit="s",
            description="External-task execution duration.",
        )
        self.active_executions: UpDownCounter = self.meter.create_up_down_counter(
            "fastbpmn.external_task.active_executions",
            unit="{execution}",
            description="External-task executions currently being handled.",
        )
        self.lock_requests: Counter = self.meter.create_counter(
            "fastbpmn.external_task.lock_requests",
            unit="{request}",
            description="External-task lock decisions.",
        )
        self.framework_operations: Counter = self.meter.create_counter(
            "fastbpmn.external_task.framework_operations",
            unit="{operation}",
            description="Nested fastbpmn framework operations.",
        )

    def create_state(self, attributes: dict[str, str]) -> _MetricsState:
        return _MetricsState(attributes)

    def receive_event(self, state: _MetricsState, event: Mapping[str, Any]) -> None:
        event_name = event_type(event)
        if event_name == "externaltask.execute.start" and not state.active:
            state.started_at = time.perf_counter()
            state.active = True
            self.record(self.active_executions.add, 1, state.attributes)
        elif event_name == "externaltask.end" and state.active:
            self.finish_execution(state, "cancelled")

        response = OPERATION_RESPONSES.get(event_name)
        transaction = event.get("transaction")
        if response is not None and isinstance(transaction, str):
            self.finish_operation(state, transaction, response[1])

    def send_event(self, state: _MetricsState, event: Mapping[str, Any]) -> None:
        event_name = event_type(event)
        if event_name in ("externaltask.lock.accept", "externaltask.lock.reject"):
            outcome = "accepted" if event_name.endswith("accept") else "rejected"
            self.record(
                self.lock_requests.add,
                1,
                {**state.attributes, "outcome": outcome},
            )

        operation = OPERATION_REQUESTS.get(event_name)
        transaction = event.get("transaction")
        if operation is not None and isinstance(transaction, str):
            state.operations[transaction] = operation

        outcome = TERMINAL_EVENTS.get(event_name)
        if outcome is not None and state.active:
            self.finish_execution(state, outcome)

    def finish_state(self, state: _MetricsState) -> None:
        if state.active:
            self.finish_execution(state, "cancelled")
        for transaction in tuple(state.operations):
            self.finish_operation(state, transaction, False)

    def finish_execution(self, state: _MetricsState, outcome: str) -> None:
        if not state.active or state.finished:
            return
        state.active = False
        state.finished = True
        attributes = {**state.attributes, "outcome": outcome}
        self.record(self.executions.add, 1, attributes)
        self.record(self.active_executions.add, -1, state.attributes)
        if state.started_at is not None:
            self.record(
                self.execution_duration.record,
                time.perf_counter() - state.started_at,
                attributes,
            )

    def finish_operation(
        self,
        state: _MetricsState,
        transaction: str,
        success: bool,
    ) -> None:
        operation = state.operations.pop(transaction, None)
        if operation is None:
            return
        self.record(
            self.framework_operations.add,
            1,
            {
                **state.attributes,
                "operation": operation,
                "outcome": "success" if success else "failure",
            },
        )
