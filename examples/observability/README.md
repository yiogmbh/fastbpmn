# fastbpmn Observability Example

This example runs the same two-task Camunda 7 process as the
`examples/camunda7` example, with OpenTelemetry metrics and tracing enabled.
The trace and metric data are written to the worker's console, so no collector
or telemetry account is required.

## Prerequisites

- Docker with Compose support

## Running

From this directory, run:

```shell
docker compose up --build
```

The Compose services will start Camunda 7, deploy `example.bpmn`, start one
process instance, and run the fastbpmn worker. The worker console should show
the `fastbpmn external task` spans and metrics including:

- `fastbpmn.external_task.executions`
- `fastbpmn.external_task.execution_duration`
- `fastbpmn.external_task.active_executions`

The process executes the `build-greeting` task followed by the `greet` task.

## Remarks

The example uses an in-memory H2 database. The worker installs the
`fastbpmn[observability]` extra through the script metadata in
`example.py`; the base fastbpmn package does not require OpenTelemetry.
