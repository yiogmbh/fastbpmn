# Observability

fastbpmn can emit OpenTelemetry traces and metrics for external-task
executions. OpenTelemetry is optional and the base `fastbpmn` installation does
not install an SDK or exporter.

## Installation

Install the built-in observability integration in the application running the
worker:

```shell
uv add "fastbpmn[observability]"
```

For OTLP export, also install the exporter extra:

```shell
uv add "fastbpmn[observability,observability-otlp]"
```

The application owns provider and exporter configuration. fastbpmn only gets a
tracer and meter and does not configure global providers.

## Console Verification

Console exporters are useful for checking the integration before connecting a
collector or backend:

```python
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from fastbpmn import FastBPMN
from fastbpmn.middleware import Middleware
from fastbpmn.middleware.metrics import MetricsMiddleware
from fastbpmn.middleware.tracing import TracingMiddleware


trace_provider = TracerProvider()
trace_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(trace_provider)

metric_reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter(),
    export_interval_millis=5_000,
)
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))

app = FastBPMN(
    # Tracing is outermost so metrics are recorded in the active span context.
    middleware=[
        Middleware(TracingMiddleware),
        Middleware(MetricsMiddleware),
    ],
)
```

To enable both signals with one registration, use the equivalent convenience
middleware:

```python
from fastbpmn.middleware import Middleware
from fastbpmn.middleware.observability import ObservabilityMiddleware

app = FastBPMN(middleware=[Middleware(ObservabilityMiddleware)])
```

`MetricsMiddleware` and `TracingMiddleware` can also be enabled independently.

Tracing records exception type, message, and stack trace using the standard
OpenTelemetry exception event by default. To keep exception messages out of
telemetry, pass `record_exception_details=False` to `TracingMiddleware` or
`ObservabilityMiddleware`; the middleware will retain only the exception type.

Run a worker with this setup and execute one external task. The console should
contain a `fastbpmn external task` span with an `execution.outcome` attribute,
as well as `fastbpmn.external_task.executions` and
`fastbpmn.external_task.execution_duration` metrics. Metric export is periodic,
so keep the worker running for at least five seconds or flush/shutdown the
meter provider during application shutdown.

The complete worker setup is available in
`examples/observability/example.py`.

## Signals

The middleware records:

- A scope span from `externaltask.start` to `externaltask.end`.
- A lock span from `externaltask.lock.request` to lock acceptance or rejection.
- An execution-negotiation span from `externaltask.execute.request` to execute
  acceptance or rejection.
- An execution span from `externaltask.execute.start` to a terminal execution
  event.
- Execution count, duration, active executions, and lock-decision metrics.
- Child spans and outcome metrics for signal emission, message correlation,
  and variable fetch operations.

Protocol event names are preserved as span events and `aetpi.*` attributes.
Lock extensions are recorded as protocol events and do not create short-lived
spans. Variable fetches are children of the execution span because they occur
while a task handler is running.

Topic and process-definition key are used as bounded dimensions. Variables,
business keys, process instance IDs, task IDs, error messages, and other
payloads are not exported as span attributes or metric dimensions. Exception
details are the exception to this rule and can be disabled as described above.

## Production Export

Replace the console span processor and metric reader with the OTLP exporters or
another OpenTelemetry-compatible exporter. The fastbpmn middleware registration
does not change when changing exporters.
