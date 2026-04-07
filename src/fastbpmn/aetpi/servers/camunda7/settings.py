import logging
import re
from typing import Annotated

from annotated_types import Ge
from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Camunda7Settings(BaseSettings):
    name: str | None = None

    tenants: Annotated[list[str], Field(default_factory=list)]

    workers: Annotated[int, Ge(1)] = 10

    shuffle_pending: bool = True

    business_key_alike: re.Pattern | None = None

    camunda_url: HttpUrl | None = None

    camunda_username: str | None = None
    camunda_password: str | None = None

    camunda_timeout: float | None = None

    @model_validator(mode="after")
    def warn_if_user_and_pass_set_twice(self):

        if self.business_key_alike is not None:
            logger.warning(
                "business_key_alike is deprecated, consider migrating to tenants instead"
            )

        if self.camunda_url and self.camunda_url.username and self.camunda_username:
            logger.warning(
                "camunda_url contains username, and camunda_username are set both"
            )

        if self.camunda_url and self.camunda_url.password and self.camunda_password:
            logger.warning(
                "camunda_url contains password, and camunda_password are set both"
            )

        return self

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
