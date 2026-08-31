---
icon: lucide/rocket
---

![fastbpmn logo](assets/logo.svg)

# Get started

## Prerequisites

* [ ] a camunda7 compatible process engine (squirrel currently supports camunda7 and derivatives only)
  (look at [process engines](processengines))
* [ ] a process full of external tasks / service tasks you want to process
* [ ] a few minutes to setup your python project

## Installation

```shell
# add fastbpmn as dependency to your project
uv add fastbpmn
```

## Example

The example refers to the examples provided for each of the supported process engines (see [integrations](processengines/index.md))

The process shown below is also available as an interactive diagram. Select an
element to inspect its BPMN name and use the viewer controls to navigate the
diagram.

{{
    bpmn("assets/bpmn/greeting.bpmn", page_url=page.url, title="Greeting process", min_height="250px", config='
{
    "hello": "world",
    "snippets": [
        {
            "filename": "example.py",
            "topic": "build-greeting",
            "lineHighlights": [28,29,30,31,32,33,33]
        },
        {
            "filename": "example.py",
            "topic": "greet",
            "lineHighlights": [35, 36,37,38,39,40]
        }
    ]
}
')
}}

```python title="example.py"
from contextlib import asynccontextmanager

import structlog

import squirrel
from fastbpmn import FastBPMN
from fastbpmn.models import BaseOutputModel


logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app):
    logger.info("init your resources here")
    yield
    logger.info("ensure to properly close them here")


minion = FastBPMN(
    name="Bob",
    lifespan=lifespan
)

class Greeting(BaseOutputModel):
    greeting: str


@minion.external_task(
    topic="build-greeting",
    output_class=Greeting,
)
def build_greeting():
    return Greeting(greeting="Hello from FastBPMN")

@minion.external_task(
    topic="greet",
    input_class=Greeting,
)
def shoutout(value: Greeting):
    logger.info(f"shoutout: {value.greeting}")


if __name__ == '__main__':
    from structlog_config import configure_logger
    log = configure_logger()

    #structlog.stdlib.recreate_defaults(log_level=logging.INFO)

    squirrel.run(
        minion,
        flavour="camunda7",
        name="bob",
        workers=10,
        camunda_url=os.getenv("engine_url"),
        camunda_username=os.getenv("engine_username"),
        camunda_password=os.getenv("engine_password"),
    )
```

## Start

```shell
engine_url=<your url> uv run example.py
```
