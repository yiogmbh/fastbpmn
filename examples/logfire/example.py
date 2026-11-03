# /// script
# dependencies = [
#   "fastbpmn[observability]",
#   "logfire",
# ]
# ///
from contextlib import asynccontextmanager
import os

import logfire
import structlog

import squirrel

from fastbpmn import FastBPMN
from fastbpmn.models import BaseInputModel, BaseOutputModel
from fastbpmn.middleware.observability import (
    MetricsMiddleware,
    TracingMiddleware,
    wrap_lifespan,
)

logger = structlog.get_logger(__name__)


logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic()


@wrap_lifespan()
@asynccontextmanager
async def lifespan(app):
    logger.info("init your resources here")
    yield
    logger.info("ensure to properly close them here")


app = FastBPMN(
    name="observability-example",
    lifespan=lifespan,
)
app.add_middleware(MetricsMiddleware, include_tenant=True)
app.add_middleware(
    TracingMiddleware,
    include_tenant=True,
    include_business_key=True,
    record_variable_details=True,
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
