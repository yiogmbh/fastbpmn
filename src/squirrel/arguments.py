from typing import Annotated

import typer
from aetpiref.typing import AETPIApplication

from .parser import as_aetpi_application

SquirrelApp = Annotated[
    AETPIApplication,
    typer.Argument(envvar=["SQUIRREL_APP", "MODULE_NAME"], parser=as_aetpi_application),
]

# Todo<dh> add some restrictions here e.g. lowercasing or no spaces ...
SquirrelName = Annotated[
    str | None, typer.Option("--name", envvar=["SQUIRREL_NAME", "MINION_NAME"])
]

SquirrelWorkers = Annotated[
    int,
    typer.Option(
        "--workers",
        min=1,
        envvar=["SQUIRREL_WORKERS"],
    ),
]
