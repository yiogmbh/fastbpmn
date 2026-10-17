import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from aetpiref.typing import AETPIApplication
from opentelemetry import context, trace
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from ._observability import (
    EventLifecycleMiddleware,
    OPERATION_REQUESTS,
    OPERATION_RESPONSES,
    TERMINAL_EVENTS,
    event_type,
)

__all__ = ("TracingMiddleware",)

_INSTRUMENTATION_NAME = "fastbpmn.middleware.tracing"


@dataclass
class _TracingState:
    attributes: dict[str, str]
    scope_span: Span | None = None
    scope_context_token: Any = None
    scope_active: bool = False
    lock_span: Span | None = None
    negotiation_span: Span | None = None
    execution_span: Span | None = None
    execution_context_token: Any = None
    execution_active: bool = False
    execution_outcome: str | None = None
    exception: BaseException | None = None
    operations: dict[str, tuple[Span, str, str]] = field(default_factory=dict)


class TracingMiddleware(EventLifecycleMiddleware):
    """Create detailed OpenTelemetry spans for AETPI task lifecycles."""

    def __init__(
        self,
        app: AETPIApplication,
        *,
        tracer: Tracer | None = None,
        include_tenant: bool = False,
        record_exception_details: bool = True,
    ) -> None:
        super().__init__(app, include_tenant=include_tenant)
        self.tracer = tracer or trace.get_tracer(_INSTRUMENTATION_NAME)
        self.record_exception_details = record_exception_details

    def create_state(self, attributes: dict[str, str]) -> _TracingState:
        return _TracingState(attributes)

    def receive_event(self, state: _TracingState, event: Mapping[str, Any]) -> None:
        event_name = event_type(event)
        if event_name == "externaltask.start" and not state.scope_active:
            self.start_scope(state)

        self.record_protocol_event(state, event_name)

        if event_name == "externaltask.lock.request" and state.lock_span is None:
            state.lock_span = self.start_phase(
                state,
                "fastbpmn.external_task.lock",
                "lock",
            )
            self.record_phase_event(state.lock_span, event_name)
        elif (
            event_name == "externaltask.execute.request"
            and state.negotiation_span is None
        ):
            state.negotiation_span = self.start_phase(
                state,
                "fastbpmn.external_task.execute.negotiation",
                "execute.negotiation",
            )
            self.record_phase_event(state.negotiation_span, event_name)
        elif event_name == "externaltask.execute.start" and not state.execution_active:
            self.start_execution(state)

        response = OPERATION_RESPONSES.get(event_name)
        transaction = event.get("transaction")
        if response is not None and isinstance(transaction, str):
            self.finish_operation(state, transaction, response[1], event_name)

        if event_name == "externaltask.end":
            if state.execution_active:
                self.finish_execution(state, "cancelled")
            self.finish_phase(state, "lock_span", "cancelled")
            self.finish_phase(state, "negotiation_span", "cancelled")
            self.finish_scope(state, state.execution_outcome or "completed")

    def send_event(self, state: _TracingState, event: Mapping[str, Any]) -> None:
        event_name = event_type(event)
        self.record_protocol_event(state, event_name)

        if event_name in ("externaltask.lock.accept", "externaltask.lock.reject"):
            self.finish_phase(
                state,
                "lock_span",
                "accepted" if event_name.endswith("accept") else "rejected",
                event_name,
            )
        elif event_name in (
            "externaltask.execute.accept",
            "externaltask.execute.reject",
        ):
            self.finish_phase(
                state,
                "negotiation_span",
                "accepted" if event_name.endswith("accept") else "rejected",
                event_name,
            )

        operation = OPERATION_REQUESTS.get(event_name)
        transaction = event.get("transaction")
        if operation is not None and isinstance(transaction, str):
            self.start_operation(state, transaction, operation, event_name)

        outcome = TERMINAL_EVENTS.get(event_name)
        if outcome is not None and state.execution_active:
            self.finish_execution(state, outcome, event_name=event_name)

    def handle_exception(self, state: _TracingState, exc: BaseException) -> None:
        state.exception = exc

    def finish_state(self, state: _TracingState) -> None:
        outcome = (
            "cancelled" if isinstance(state.exception, asyncio.CancelledError) else None
        )
        if state.execution_active:
            self.finish_execution(state, outcome or "exception", exc=state.exception)
        self.finish_phase(state, "lock_span", outcome or "exception")
        self.finish_phase(state, "negotiation_span", outcome or "exception")
        for transaction in tuple(state.operations):
            self.finish_operation(state, transaction, False, None)
        if state.scope_active:
            self.finish_scope(state, outcome or state.execution_outcome or "cancelled")

    def start_scope(self, state: _TracingState) -> None:
        state.scope_active = True
        state.scope_span = self.start_span(
            "fastbpmn.external_task.scope",
            state.attributes,
        )
        if state.scope_span is not None:
            try:
                state.scope_context_token = context.attach(
                    trace.set_span_in_context(state.scope_span)
                )
            except Exception:
                self.record(state.scope_span.end)
                state.scope_span = None

    def start_execution(self, state: _TracingState) -> None:
        state.execution_active = True
        state.execution_span = self.start_span(
            "fastbpmn.external_task.execute",
            {**state.attributes, "aetpi.phase": "execute"},
        )
        self.record_phase_event(state.execution_span, "externaltask.execute.start")
        if state.execution_span is not None:
            try:
                state.execution_context_token = context.attach(
                    trace.set_span_in_context(state.execution_span)
                )
            except Exception:
                self.record(state.execution_span.end)
                state.execution_span = None

    def start_phase(
        self,
        state: _TracingState,
        name: str,
        phase: str,
    ) -> Span | None:
        return self.start_span(
            name,
            {**state.attributes, "aetpi.phase": phase},
        )

    def start_operation(
        self,
        state: _TracingState,
        transaction: str,
        operation: str,
        event_name: str,
    ) -> None:
        span = self.start_span(
            f"fastbpmn.external_task.{operation}",
            {
                **state.attributes,
                "aetpi.phase": operation,
                "aetpi.request.type": event_name,
            },
        )
        if span is not None:
            state.operations[transaction] = (span, operation, event_name)
            self.record(span.add_event, event_name, {"aetpi.event.type": event_name})

    def record_phase_event(self, span: Span | None, event_name: str) -> None:
        if span is not None:
            self.record(span.add_event, event_name, {"aetpi.event.type": event_name})

    def finish_operation(
        self,
        state: _TracingState,
        transaction: str,
        success: bool,
        event_name: str | None,
    ) -> None:
        operation_data = state.operations.pop(transaction, None)
        if operation_data is None:
            return
        span, _, _ = operation_data
        if event_name is not None:
            self.record(
                span.add_event,
                event_name,
                {"aetpi.event.type": event_name},
            )
            self.record(span.set_attribute, "aetpi.response.type", event_name)
        self.record(
            span.set_attribute, "operation.outcome", "success" if success else "failure"
        )
        if not success:
            self.record(span.set_status, Status(StatusCode.ERROR))
        self.record(span.end)

    def finish_execution(
        self,
        state: _TracingState,
        outcome: str,
        event_name: str | None = None,
        exc: BaseException | None = None,
    ) -> None:
        if not state.execution_active:
            return
        state.execution_active = False
        state.execution_outcome = outcome
        if state.execution_span is not None:
            self.record(
                state.execution_span.set_attribute, "execution.outcome", outcome
            )
        self.finish_span(
            state.execution_span,
            outcome,
            event_name,
            state.execution_context_token,
            exc,
        )
        state.execution_span = None
        state.execution_context_token = None

    def finish_scope(self, state: _TracingState, outcome: str) -> None:
        if not state.scope_active:
            return
        state.scope_active = False
        self.finish_span(
            state.scope_span,
            outcome,
            None,
            state.scope_context_token,
            state.exception,
        )
        state.scope_span = None
        state.scope_context_token = None

    def finish_phase(
        self,
        state: _TracingState,
        field: str,
        outcome: str,
        event_name: str | None = None,
    ) -> None:
        span = getattr(state, field)
        if span is None:
            return
        if event_name is not None:
            self.record(span.add_event, event_name, {"aetpi.event.type": event_name})
            self.record(span.set_attribute, "aetpi.response.type", event_name)
        self.record(span.set_attribute, "aetpi.outcome", outcome)
        if outcome in {"exception", "failure"}:
            self.record(span.set_status, Status(StatusCode.ERROR))
        self.record(span.end)
        setattr(state, field, None)

    def record_protocol_event(self, state: _TracingState, event_name: str) -> None:
        spans = (
            state.scope_span,
            state.lock_span,
            state.negotiation_span,
            state.execution_span,
        )
        seen: set[int] = set()
        for span in spans:
            if span is not None and id(span) not in seen:
                seen.add(id(span))
                self.record(
                    span.add_event,
                    event_name,
                    {"aetpi.event.type": event_name},
                )

    def start_span(self, name: str, attributes: dict[str, str]) -> Span | None:
        try:
            return self.tracer.start_span(name, attributes=attributes)
        except Exception:
            return None

    def finish_span(
        self,
        span: Span | None,
        outcome: str,
        event_name: str | None,
        token: Any,
        exc: BaseException | None,
    ) -> None:
        if span is None:
            return
        if event_name is not None:
            self.record(span.set_attribute, "aetpi.response.type", event_name)
        self.record(span.set_attribute, "aetpi.outcome", outcome)
        if outcome in {"failure", "business_error", "exception"}:
            self.record(span.set_status, Status(StatusCode.ERROR))
        elif outcome in {"completed", "accepted"}:
            self.record(span.set_status, Status(StatusCode.OK))
        if exc is not None:
            if self.record_exception_details:
                self.record(span.record_exception, exc)
            else:
                self.record(
                    span.add_event,
                    "exception",
                    {"exception.type": type(exc).__name__},
                )
        if token is not None:
            self.record(context.detach, token)
        self.record(span.end)
