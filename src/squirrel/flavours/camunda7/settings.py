from fastbpmn.aetpi.servers.camunda7.settings import Camunda7Settings


class Camunda7SquirrelSettings(Camunda7Settings):
    @property
    def flavour(self) -> str:
        return "camunda7"

    def as_kwargs(self) -> dict:
        return self.model_dump(
            mode="python",
            by_alias=True,
            exclude_unset=True,
            exclude_defaults=True,
        )
