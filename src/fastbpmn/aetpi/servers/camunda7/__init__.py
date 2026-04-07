import logging
import re

from aetpiref.typing import AETPIApplication
from pydantic import HttpUrl

from .server import Camunda7Server

logger = logging.getLogger(__name__)


def run(
    app: AETPIApplication,
    *,
    name: str,
    parallelism: int = 10,
    shuffle_pending: bool = True,
    tenant_ids: list[str] | None = None,
    business_key_alike: re.Pattern | None = None,
    camunda_base_url: HttpUrl | str = None,
    camunda_username: str | None = None,
    camunda_password: str | None = None,
    camunda_timeout: float | None = None,
):

    if business_key_alike is not None:
        logger.warning(
            "[DEPRECATED] consider using tenants instead of business_key_alike"
        )

    Camunda7Server(
        app,
        name=name,
        parallelism=parallelism,
        shuffle_pending=shuffle_pending,
        tenant_ids=tenant_ids,
        business_key_alike=business_key_alike,
        camunda_base_url=camunda_base_url,
        camunda_username=camunda_username,
        camunda_password=camunda_password,
        camunda_timeout=camunda_timeout,
    ).run()


__all__ = ["run"]
