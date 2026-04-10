# CIBSeven

[CIBSeven](https://cibseven.org) is an open-source Camunda 7 fork. fastbpmn is fully compatible with it —
the `camunda7` flavour works out of the box.

This guide walks you through a [self-contained example](https://github.com/yiogmbh/fastbpmn/tree/main/examples/cibseven/)
that:

1. Starts a local CIBSeven instance
2. Deploys a BPMN process
3. Starts a process instance
4. Runs a fastbpmn worker that handles the external tasks

## The Process

The example process (`example.bpmn`) has two consecutive external service tasks:

| Topic | What it does |
|---|---|
| `build-greeting` | Receives a `greeter` input variable, builds a greeting string, and returns it as `shoutout` |
| `greet` | Receives `shoutout` and logs it |

## Project Structure

```
examples/cibseven/
├── docker-compose.yaml   # full local environment
├── Dockerfile            # builds the fastbpmn worker image
├── example.bpmn          # the process definition
└── example.py            # the fastbpmn worker
```

## The Worker

The worker (`example.py`) registers two external task handlers against a `FastBPMN` instance and then
starts it via `squirrel.run` using the `camunda7` flavour.

```python title="example.py"
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

    configure_logger()

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

The connection details are passed in via environment variables so the same image works both locally and
in any other environment.

## Running the Example

Everything is wired up in `docker-compose.yaml`. A single command brings up the full stack:

```shell
cd examples/cibseven
docker compose up
```

Docker Compose orchestrates the startup in the right order:

```
cibseven (healthy)
    ├── deploy   → POSTs example.bpmn to /deployment/create, then exits
    │       └── start  → POSTs to /process-definition/key/example/start, then exits
    └── fastbpmn → polls for external tasks and processes them
```

1. **`cibseven`** — starts the engine with an in-memory H2 database and waits until its REST API is up
2. **`deploy`** — uploads `example.bpmn` via the REST API once the engine is healthy
3. **`start`** — triggers one process instance after the deployment completes
4. **`fastbpmn`** — the Python worker, picks up the two external tasks and logs the greeting

You should see log output from the worker similar to:

```
2026-04-09T13:31:47.461758Z [info     ] Waiting for application startup. [fastbpmn.lifespan]
2026-04-09T13:31:47.461932920Z 2026-04-09T13:31:47.461853Z [info     ] init your resources here
2026-04-09T13:31:47.462027004Z 2026-04-09T13:31:47.461939Z [info     ] Application startup complete.  [fastbpmn.lifespan]
2026-04-09T13:31:47.462129795Z 2026-04-09T13:31:47.462027Z [info     ] Match predicate: (tenant_id=*) && (process_definition_key=*) && (topic_name={'build-greeting'}) task_properties=TaskProperties(process_definition_key=None, topic='build-greeting', lock_duration=300000, handler=<function build_greeting at 0xffff9e498cc0>, retries=3, retry_timeout=1000, input_class=<class '__main__.BuildGreetingInput'>, output_class=<class '__main__.BuildGreetingOutput'>, title='build_greeting', description=None, tenants=None)
2026-04-09T13:31:47.462171212Z 2026-04-09T13:31:47.462086Z [info     ] Match predicate: (tenant_id=*) && (process_definition_key=*) && (topic_name={'greet'}) task_properties=TaskProperties(process_definition_key=None, topic='greet', lock_duration=300000, handler=<function shoutout at 0xffff9e498d60>, retries=3, retry_timeout=1000, input_class=<class '__main__.GreetInput'>, output_class=None, title='shoutout', description=None, tenants=None)
2026-04-09T13:31:48.543224629Z 2026-04-09T13:31:48.543065Z [info     ] Hello, I'm yio gmbh! I'm saying hello from FastBPMN scope={'type': 'externaltask', 'protocol': 'camunda7', 'aetpi': {'version': '1.0', 'spec_version': '1.0'}, 'task': {'activity_id': 'Activity_0sla1xu', 'activity_instance_id': 'Activity_0sla1xu:7580a361-3418-11f1-afbf-d202db1960ee', 'process_definition_id': 'example:1:6b14a384-3418-11f1-afbf-d202db1960ee', 'process_definition_key': 'example', 'process_definition_version_tag': None, 'id': '7580ca74-3418-11f1-afbf-d202db1960ee', 'execution_id': '7580a360-3418-11f1-afbf-d202db1960ee', 'process_instance_id': '6b673055-3418-11f1-afbf-d202db1960ee', 'topic_name': 'greet', 'business_key': None, 'priority': 0, 'retries': None, 'worker_id': 'bob-616ec2af', 'suspended': False, 'lock_expiration_time': None, 'error_message': None, 'tenant_id': None, 'retry_timeout': 1000, 'lock_duration': 300000, 'title': 'shoutout', 'description': None}} worker_id=bob-616ec2af
```

## Connecting to Your Own CIBSeven Instance

To point the worker at an existing CIBSeven (or Camunda 7) engine instead of the local one, pass the
environment variables directly:

```shell
engine_url=https://your-engine/engine-rest/ \
engine_username=demo \
engine_password=demo \
uv run example.py
```

Or set them in a `.env` file — fastbpmn picks them up automatically via `pydantic-settings`.
