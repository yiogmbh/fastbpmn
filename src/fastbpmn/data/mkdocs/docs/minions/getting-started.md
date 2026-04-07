class Field:
pass# Getting Started

The following examples should help to get started with `yio-minions` quickly.

## First Steps

Consider you have a simple bpmn process that looks like this. The only topic included
is `say-hello`.

```{.bpmn}
--8<-- "docs/minions/example.bpmn"
```

```python title="minion.py"
from pydantic import Field

from fastbpmn import YioMinion
from fastbpmn.camunda import ProcessEngine
from fastbpmn.model import BaseInputModel, BaseOutputModel

pe = ProcessEngine(
    camunda_base_url="https://pe.yio.at"
)
minion = YioMinion(process_engine=pe, name="Bob")


class SayHelloInput(BaseInputModel):
    name: str = Field(..., title="Name", description="The person to be greeted.", example="Tim")


@minion.external_task(
    topic="say-hello",
    input_class=SayHelloInput,
)
async def say_hello(params: SayHelloInput):
    """
    A simple external task, acting as the business logic in the example process.
    """
    print(f"Hello {params.name}")


# To start simply call the minion itself
# There are two commands supported by the bootstrapped command line interface
#   run      : Executes the minion and tries to work on external tasks
#   info     : Simply tells you something about the minions capabilities
if __name__ == '__main__':
    minion()
```

Your minion is now ready to work, starting is as simple as:

<div class="termy" style="max-height: 200px">

```console
$ python minion.py run
Minion: Bob
Process: None - Topics: say-hello
Bob reports for duty
```

</div>

### Check for capabilities

You can ask your minion to tell you for which process he is responsible.

<div class="termy" style="max-height: 200px">

```console
$ python minion.py info
Minion: Bob
Process: None - Topics: say-hello
```

</div>
