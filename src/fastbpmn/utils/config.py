import os
from typing import Annotated, Union

from pydantic import AfterValidator, AnyUrl, Field, HttpUrl
from pydantic_core import Url
from pydantic_settings import BaseSettings as PydanticBaseSettings
from pydantic_settings import SettingsConfigDict


class BaseSettings(PydanticBaseSettings):
    """
    Base Settings (derive this class when implementing your own setting classes
    dependent on .env files (for example).

    Simply create a .env file (to change the filename use the ENV_FILE environment variable).
    """

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"), env_file_encoding="utf-8"
    )


def check_username(v: Url) -> Url:
    """
    Check if username is present in URL
    """
    if not v.username:
        raise ValueError("Username missing in URL")
    return v


def check_password(v: Url) -> Url:
    """
    Check if password is present in URL
    """
    if not v.password:
        raise ValueError("Password missing in URL")
    return v


ProtectedUrl = Annotated[
    Union[HttpUrl, AnyUrl],
    AfterValidator(check_username),
    AfterValidator(check_password),
]


class ProtectedUrlSettings(BaseSettings):
    """
    An abstract definition ...
    """

    url: ProtectedUrl = Field(
        ...,
        title="Protected URL",
        description="The connection string with username and password",
    )
