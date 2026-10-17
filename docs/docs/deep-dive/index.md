---
icon: lucide/book-open
---
# Deep Dive

This guide follows one process from its BPMN model to a running fastbpmn
worker. Start with the [getting-started guide](../index.md), then use this
page to understand how the pieces fit together.

## 1. Model the process

The process model identifies the external tasks and their topics. The example
below has two external tasks: one creates a greeting and the next consumes it.

{{ bpmn("assets/bpmn/greeting.bpmn", page_url=page.url, title="Greeting process") }}

The topic is the contract between the BPMN model and the Python application.
The handler that subscribes to `build-greeting` can be selected independently
of the process definition.

## 2. Create the application

Create a `FastBPMN` application and register external-task handlers on it:

```python
from fastbpmn import FastBPMN
from fastbpmn.models import BaseOutputModel

minion = FastBPMN(name="Bob")


class Greeting(BaseOutputModel):
    greeting: str


@minion.external_task(topic="build-greeting", output_class=Greeting)
def build_greeting() -> Greeting:
    return Greeting(greeting="Hello from FastBPMN")


@minion.external_task(topic="build-greeting", input_class=Greeting)
def shoutout(value: Greeting) -> None:
    print(value.greeting)
```

Typed models make the variable contract visible in the handler signature and
allow fastbpmn to validate values at the process boundary.

## 3. Run the worker

The `squirrel` runner connects the application to a supported process engine:

```python
import squirrel

squirrel.run(
    minion,
    flavour="camunda7",
    name="bob",
    workers=10,
    camunda_url="http://localhost:8080/engine-rest",
)
```

Keep engine-specific settings in configuration or environment variables when
deploying. See the [process-engine integrations](../processengines/index.md)
for engine-specific setup.

## 4. Handle outcomes

Handlers can return successful values or raise the appropriate fastbpmn result
types when work should be retried, reported as a business error, or stopped as
a fatal failure. The [features](../features/index.md) section provides the
details for each result type.

## 5. Test handlers

Keep business logic testable independently of the process engine. Construct
the input model in a unit test, call the handler, and test the returned model
or raised result. Use engine-level tests only for routing, variable mapping,
and the integration boundary.
