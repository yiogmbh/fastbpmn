# /// script
# dependencies = [
#   "fastbpmn[observability]",
# ]
# ///
from contextlib import asynccontextmanager
import os

import structlog
import squirrel
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
from fastbpmn.models import BaseInputModel, BaseOutputModel
from fastbpmn.middleware import Middleware
from fastbpmn.middleware.metrics import MetricsMiddleware
from fastbpmn.middleware.tracing import TracingMiddleware

logger = structlog.get_logger(__name__)


def configure_console_telemetry() -> None:
    """Configure local exporters before creating the worker application."""
    trace_provider = TracerProvider()
    trace_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(trace_provider)

    metric_reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(),
        export_interval_millis=5_000,
    )
    metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))


configure_console_telemetry()


@asynccontextmanager
async def lifespan(app):
    logger.info("init your resources here")
    yield
    logger.info("ensure to properly close them here")


app = FastBPMN(
    name="observability-example",
    lifespan=lifespan,
    middleware=[
        Middleware(TracingMiddleware),
        Middleware(MetricsMiddleware),
    ],
)


class BuildGreetingInput(BaseInputModel):
    greeter: str


class BuildGreetingOutput(BaseOutputModel):
    shoutout: str


class GreetInput(BaseInputModel):
    shoutout: str


@app.external_task(
    topic="build-greeting",
    input_class=BuildGreetingInput,
    output_class=BuildGreetingOutput,
)
def build_greeting(value: BuildGreetingInput) -> BuildGreetingOutput:
    return BuildGreetingOutput(
        shoutout=f"Hello, I'm {value.greeter}! I'm saying hello from FastBPMN"
    )


@app.external_task(topic="greet", input_class=GreetInput)
def shoutout(value: GreetInput) -> None:
    logger.info("received greeting", shoutout=value.shoutout)


if __name__ == "__main__":
    squirrel.run(
        app,
        flavour="camunda7",
        name="observability-example",
        workers=1,
        camunda_url=os.getenv("engine_url"),
        camunda_username=os.getenv("engine_username"),
        camunda_password=os.getenv("engine_password"),
    )
