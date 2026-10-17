from unittest.mock import AsyncMock

import pytest
from aetpiref.typing import AETPIReceiveEvent
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from fastbpmn.middleware.observability import ObservabilityMiddleware
from fastbpmn.middleware.metrics import MetricsMiddleware
from fastbpmn.middleware.tracing import TracingMiddleware


DEFAULT_SCOPE = {
    "type": "externaltask",
    "protocol": "camunda7",
    "aetpi": {"spec_version": "1.0", "version": "1.0"},
    "task": {
        "topic_name": "test-topic",
        "process_definition_key": "test-process",
        "tenant_id": "test-tenant",
    },
}


def telemetry():
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    return tracer_provider, meter_provider, span_exporter, metric_reader


async def receive_events(
    events: list[AETPIReceiveEvent],
) -> AETPIReceiveEvent:
    return events.pop(0)


@pytest.mark.asyncio
async def test_non_external_task_is_passthrough() -> None:
    app = AsyncMock()
    middleware = ObservabilityMiddleware(app)
    receive = AsyncMock()
    send = AsyncMock()

    await middleware({"type": "http"}, receive, send)  # type: ignore[arg-type]

    app.assert_awaited_once_with({"type": "http"}, receive, send)


@pytest.mark.asyncio
async def test_successful_execution_records_span_and_metrics() -> None:
    tracer_provider, meter_provider, span_exporter, metric_reader = telemetry()
    incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.execute.start"},
        {"type": "externaltask.end"},
    ]

    async def app(
        scope: dict[str, object],
        receive,
        send,
    ) -> None:
        await receive()
        await receive()
        await send({"type": "externaltask.execute.complete"})
        await receive()

    middleware = ObservabilityMiddleware(
        app,
        tracer=tracer_provider.get_tracer("test"),
        meter=meter_provider.get_meter("test"),
    )
    await middleware(
        DEFAULT_SCOPE,
        lambda: receive_events(incoming),
        AsyncMock(),
    )

    spans = span_exporter.get_finished_spans()
    assert {span.name for span in spans} == {
        "fastbpmn.external_task.scope",
        "fastbpmn.external_task.execute",
    }
    execution_span = next(
        span for span in spans if span.name == "fastbpmn.external_task.execute"
    )
    scope_span = next(
        span for span in spans if span.name == "fastbpmn.external_task.scope"
    )
    assert execution_span.attributes["execution.outcome"] == "completed"
    assert scope_span.attributes["aetpi.outcome"] == "completed"
    assert execution_span.attributes["fastbpmn.topic"] == "test-topic"
    assert "fastbpmn.tenant_id" not in execution_span.attributes

    metrics = metric_reader.get_metrics_data().resource_metrics[0].scope_metrics[0]
    metric_names = {metric.name for metric in metrics.metrics}
    assert "fastbpmn.external_task.executions" in metric_names
    assert "fastbpmn.external_task.execution_duration" in metric_names
    assert "fastbpmn.external_task.active_executions" in metric_names


@pytest.mark.asyncio
async def test_metrics_and_tracing_can_be_enabled_independently() -> None:
    tracer_provider, meter_provider, span_exporter, metric_reader = telemetry()
    metrics_incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.execute.start"},
    ]
    tracing_incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.execute.start"},
    ]

    async def complete(scope, receive, send) -> None:
        await receive()
        await receive()
        await send({"type": "externaltask.execute.complete"})

    await MetricsMiddleware(
        complete,
        meter=meter_provider.get_meter("metrics-only"),
    )(
        DEFAULT_SCOPE,
        lambda: receive_events(metrics_incoming),
        AsyncMock(),
    )
    await TracingMiddleware(
        complete,
        tracer=tracer_provider.get_tracer("tracing-only"),
    )(
        DEFAULT_SCOPE,
        lambda: receive_events(tracing_incoming),
        AsyncMock(),
    )

    assert len(span_exporter.get_finished_spans()) == 2
    metrics = metric_reader.get_metrics_data().resource_metrics[0].scope_metrics
    assert metrics


@pytest.mark.asyncio
async def test_protocol_phases_are_spans_and_lock_extension_is_an_event() -> None:
    tracer_provider, _, span_exporter, _ = telemetry()
    incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.lock.request"},
        {"type": "externaltask.execute.request"},
        {"type": "externaltask.execute.start"},
        {"type": "externaltask.end"},
    ]

    async def app(scope, receive, send) -> None:
        await receive()
        await receive()
        await send({"type": "externaltask.lock.accept"})
        await receive()
        await send({"type": "externaltask.execute.accept"})
        await receive()
        await send({"type": "externaltask.execute.extendlock", "lock_duration": 100})
        await send({"type": "externaltask.execute.complete"})
        await receive()

    middleware = TracingMiddleware(
        app,
        tracer=tracer_provider.get_tracer("test"),
    )
    await middleware(
        DEFAULT_SCOPE,
        lambda: receive_events(incoming),
        AsyncMock(),
    )

    spans = span_exporter.get_finished_spans()
    assert {span.name for span in spans} == {
        "fastbpmn.external_task.scope",
        "fastbpmn.external_task.lock",
        "fastbpmn.external_task.execute.negotiation",
        "fastbpmn.external_task.execute",
    }
    assert all("extendlock" not in span.name for span in spans)
    scope_span = next(
        span for span in spans if span.name == "fastbpmn.external_task.scope"
    )
    event_names = {event.name for event in scope_span.events}
    assert "externaltask.execute.extendlock" in event_names
    assert "externaltask.lock.request" in event_names
    assert "externaltask.execute.complete" in event_names


@pytest.mark.asyncio
async def test_failure_execution_records_failure_outcome() -> None:
    tracer_provider, meter_provider, span_exporter, metric_reader = telemetry()
    incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.execute.start"},
        {"type": "externaltask.end"},
    ]

    async def app(
        scope: dict[str, object],
        receive,
        send,
    ) -> None:
        await receive()
        await receive()
        await send({"type": "externaltask.execute.failure", "error_message": "secret"})
        await receive()

    middleware = ObservabilityMiddleware(
        app,
        tracer=tracer_provider.get_tracer("test"),
        meter=meter_provider.get_meter("test"),
    )
    await middleware(
        DEFAULT_SCOPE,
        lambda: receive_events(incoming),
        AsyncMock(),
    )

    span = next(
        span
        for span in span_exporter.get_finished_spans()
        if span.name == "fastbpmn.external_task.execute"
    )
    assert span.attributes["execution.outcome"] == "failure"
    assert "secret" not in str(span.attributes)
    metrics = metric_reader.get_metrics_data().resource_metrics[0].scope_metrics[0]
    executions = next(
        metric
        for metric in metrics.metrics
        if metric.name == "fastbpmn.external_task.executions"
    )
    assert executions.data.data_points[0].attributes["outcome"] == "failure"


@pytest.mark.asyncio
async def test_nested_operation_is_child_span_and_records_outcome() -> None:
    tracer_provider, meter_provider, span_exporter, metric_reader = telemetry()
    incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.execute.start"},
        {"type": "externaltask.signal.emitted", "transaction": "tx-1"},
        {"type": "externaltask.end"},
    ]

    async def app(
        scope: dict[str, object],
        receive,
        send,
    ) -> None:
        await receive()
        await receive()
        await send({"type": "externaltask.signal.emit", "transaction": "tx-1"})
        await receive()
        await send({"type": "externaltask.execute.complete"})
        await receive()

    middleware = ObservabilityMiddleware(
        app,
        tracer=tracer_provider.get_tracer("test"),
        meter=meter_provider.get_meter("test"),
    )
    await middleware(
        DEFAULT_SCOPE,
        lambda: receive_events(incoming),
        AsyncMock(),
    )

    spans = span_exporter.get_finished_spans()
    assert {span.name for span in spans} == {
        "fastbpmn.external_task.scope",
        "fastbpmn.external_task.execute",
        "fastbpmn.external_task.signal",
    }
    execution_span = next(
        span for span in spans if span.name == "fastbpmn.external_task.execute"
    )
    operation_span = next(
        span for span in spans if span.name == "fastbpmn.external_task.signal"
    )
    assert operation_span.parent is not None
    assert operation_span.parent.span_id == execution_span.context.span_id

    metrics = metric_reader.get_metrics_data().resource_metrics[0].scope_metrics[0]
    operations = next(
        metric
        for metric in metrics.metrics
        if metric.name == "fastbpmn.external_task.framework_operations"
    )
    assert operations.data.data_points[0].attributes["outcome"] == "success"


@pytest.mark.asyncio
async def test_exception_closes_span_and_is_reraised() -> None:
    tracer_provider, meter_provider, span_exporter, _ = telemetry()
    incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.execute.start"},
    ]

    async def app(
        scope: dict[str, object],
        receive,
        send,
    ) -> None:
        await receive()
        await receive()
        raise ValueError("secret message")

    middleware = ObservabilityMiddleware(
        app,
        tracer=tracer_provider.get_tracer("test"),
        meter=meter_provider.get_meter("test"),
    )
    with pytest.raises(ValueError, match="secret message"):
        await middleware(
            DEFAULT_SCOPE,
            lambda: receive_events(incoming),
            AsyncMock(),
        )

    span = next(
        span
        for span in span_exporter.get_finished_spans()
        if span.name == "fastbpmn.external_task.execute"
    )
    assert span.attributes["execution.outcome"] == "exception"
    assert span.events[-1].name == "exception"
    assert span.events[-1].attributes["exception.type"] == "ValueError"
    assert span.events[-1].attributes["exception.message"] == "secret message"
    assert span.events[-1].attributes["exception.stacktrace"]


@pytest.mark.asyncio
async def test_telemetry_failure_does_not_fail_application() -> None:
    class BrokenTracer:
        def start_span(self, *args, **kwargs):
            raise RuntimeError("telemetry unavailable")

    incoming = [
        {"type": "externaltask.start"},
        {"type": "externaltask.execute.start"},
    ]

    async def app(scope, receive, send) -> None:
        await receive()
        await receive()
        await send({"type": "externaltask.execute.complete"})

    middleware = ObservabilityMiddleware(app, tracer=BrokenTracer())  # type: ignore[arg-type]
    await middleware(DEFAULT_SCOPE, lambda: receive_events(incoming), AsyncMock())
