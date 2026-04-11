# /// script
# dependencies = [
#   "fastbpmn"
# ]
# ///
import os
from contextlib import asynccontextmanager

import structlog

import squirrel
from fastbpmn import FastBPMN
from fastbpmn.models import BaseOutputModel, BaseInputModel

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app):
    logger.info("init your resources here")
    yield
    logger.info("ensure to proper close them here")


minion = FastBPMN(name="Bob", lifespan=lifespan)


class BuildGreetingInput(BaseInputModel):
    greeter: str


class BuildGreetingOutput(BaseOutputModel):
    shoutout: str


class GreetInput(BaseInputModel):
    shoutout: str


@minion.external_task(
    topic="build-greeting",
    input_class=BuildGreetingInput,
    output_class=BuildGreetingOutput,
)
def build_greeting(value: BuildGreetingInput):
    return BuildGreetingOutput(
        shoutout=f"Hello, I'm {value.greeter}! I'm saying hello from FastBPMN"
    )


@minion.external_task(
    topic="greet",
    input_class=GreetInput,
)
def shoutout(value: GreetInput):
    logger.info(value.shoutout)


if __name__ == "__main__":
    from structlog_config import configure_logger

    log = configure_logger()

    # structlog.stdlib.recreate_defaults(log_level=logging.INFO)

    squirrel.run(
        minion,
        flavour="camunda7",
        name="bob",
        workers=10,
        camunda_url=os.getenv("engine_url"),
        camunda_username=os.getenv("engine_username"),
        camunda_password=os.getenv("engine_password"),
    )
