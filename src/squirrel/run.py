import re
from typing import Literal, overload

from aetpiref.typing import AETPIApplication

from squirrel.flavours.camunda7.entrypoint import camunda7
from squirrel.flavours.camunda7.settings import Camunda7SquirrelSettings
from squirrel.parser import as_aetpi_application
from squirrel.settings import SquirrelBaseSettings


@overload
def run(app: str | AETPIApplication, *, settings: SquirrelBaseSettings):
    """
    Start squirrel using an arbitrary settings instance for configuration
    """
    ...


@overload
def run(app: str | AETPIApplication, *, settings: Camunda7SquirrelSettings):
    """
    Start squirrel using camunda7 flavour providing configuration by settings
    """
    ...


@overload
def run(
    app: str | AETPIApplication,
    *,
    flavour: Literal["camunda7"],
    name: str | None = None,
    workers: int = 10,
    # camunda7 flavour specific arguments
    camunda_url: str | None = None,
    tenants: list[str] | None = None,
    business_key_alike: re.Pattern | None = None,
    shuffle_pending: bool = True,
    camunda_username: str | None = None,
    camunda_password: str | None = None,
    camunda_timeout: float | None = None,
):
    """
    Start squirrel using camunda7 flavour providing configuration by kwargs
    """
    ...


@overload
def run(
    app: str | AETPIApplication,
):
    """
    Start squirrel using defaults.
    """
    ...


def run(app: str | AETPIApplication, **kwargs):

    # try to resolve the app
    if isinstance(app, str):
        app = as_aetpi_application(app)

    if (
        "settings" in kwargs
        and kwargs["settings"] is not None
        and isinstance(kwargs["settings"], SquirrelBaseSettings)
    ):
        settings: SquirrelBaseSettings = kwargs["settings"]
        flavour = settings.flavour
        init_kwargs = settings.as_kwargs()
    else:
        flavour = kwargs.pop("flavour", "camunda7")

        init_kwargs = kwargs

    match flavour:
        case "camunda7":
            camunda7(app, **init_kwargs)

        case _:
            raise RuntimeError(f"Unknown flavour {flavour}")
