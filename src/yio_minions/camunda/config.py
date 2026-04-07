from pydantic_settings import SettingsConfigDict

from yio_minions.utils.config import ProtectedUrlSettings


class CamundaSettings(ProtectedUrlSettings):
    """
    An abstract definition containing all values related to access camunda Rest-API
    """

    model_config = SettingsConfigDict(env_prefix="camunda_")
