from pydantic.v1 import Field

from fastbpmn import YioMinion
from fastbpmn.camunda import ProcessEngine
from fastbpmn.models import BaseInputModel

pe = ProcessEngine(camunda_base_url="https://pe.yio.at/engine-rest/")
minion = YioMinion(process_engine=pe, name="Bob")


class SayHelloInput(BaseInputModel):
    name: str = Field(
        ..., title="Name", description="The person to be greeted.", example="Tim"
    )


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
if __name__ == "__main__":
    minion()
