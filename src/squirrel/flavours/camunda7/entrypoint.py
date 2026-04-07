import re
from typing import Annotated, Any

import typer
from pydantic import HttpUrl, TypeAdapter

from squirrel.arguments import SquirrelApp, SquirrelName, SquirrelWorkers
from fastbpmn.aetpi.servers.camunda7 import Camunda7Server
from fastbpmn.aetpi.servers.camunda7.settings import Camunda7Settings

http_url_adapter = TypeAdapter(HttpUrl)


def regex(value: str) -> re.Pattern:
    return re.compile(value)


def httpurl(value: str) -> HttpUrl:
    return http_url_adapter.validate_python(value)


ShufflePending = Annotated[
    bool,
    typer.Option(
        is_flag=True,
        help="Whether to shuffle pending tasks or not",
        envvar="CAMUNDA_SHUFFLE_PENDING",
    ),
]
Tenants = Annotated[
    list[str] | None,
    typer.Option(
        "--tenant",
        help="Specify the tenant(s) you be responsible for (can be repeated multiple times)",
        envvar="CAMUNDA_TENANTS",
    ),
]
BusinessKeyAlike = Annotated[
    re.Pattern | None,
    typer.Option(
        help="[DEPRECATED] A regular expression pattern to match with business keys (only tasks matching get handled)",
        parser=regex,
    ),
]
CamundaUrl = Annotated[
    HttpUrl | None,
    typer.Option(
        "--camunda-url",
        envvar="CAMUNDA_URL",
        parser=httpurl,
    ),
]


def coalesce(value: Any | None, default: Any | None = None) -> Any:
    return value if value is not None else default


camunda7_app = typer.Typer()


@camunda7_app.command()
def camunda7(
    aetpi_application: SquirrelApp,
    name: SquirrelName = None,
    workers: SquirrelWorkers = 10,
    # camunda7 flavour specific arguments
    camunda_url: CamundaUrl = None,
    tenants: Tenants = None,
    business_key_alike: BusinessKeyAlike = None,
    shuffle_pending: ShufflePending = True,
    camunda_username: str | None = None,
    camunda_password: str | None = None,
    camunda_timeout: float | None = None,
):
    """
    Start squirrel using camunda7 flavour.
    """
    settings = Camunda7Settings()

    Camunda7Server(
        aetpi_application,
        name=coalesce(name, settings.name),
        parallelism=coalesce(workers, settings.workers),
        shuffle_pending=coalesce(shuffle_pending, settings.shuffle_pending),
        tenant_ids=coalesce(tenants, settings.tenants),
        business_key_alike=coalesce(business_key_alike, settings.business_key_alike),
        camunda_url=coalesce(camunda_url, settings.camunda_url),
        camunda_username=coalesce(camunda_username, settings.camunda_username),
        camunda_password=coalesce(camunda_password, settings.camunda_password),
        camunda_timeout=coalesce(camunda_timeout, settings.camunda_timeout),
    ).run()
