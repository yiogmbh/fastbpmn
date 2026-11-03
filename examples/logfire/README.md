# fastbpmn Logfire Example

This example runs the Camunda 7 greeting process with FastBPMN tracing,
metrics, and lifespan metrics exported through Pydantic Logfire.

## Prerequisites

- Docker with Compose support
- A Logfire write token in `LOGFIRE_TOKEN`

## Running

From this directory:

```shell
export LOGFIRE_TOKEN=your-write-token
docker compose up --build
```

The worker image builds and installs `fastbpmn` from the repository checkout;
it does not download FastBPMN from PyPI. The service sends telemetry only when
`LOGFIRE_TOKEN` is present, as configured by the example.

Open the Logfire project associated with the token to inspect traces, task
metrics, and the `fastbpmn.lifespan.starts` and `fastbpmn.lifespan.up` metrics.
