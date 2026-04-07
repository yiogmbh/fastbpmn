import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


def snake2camel(snake: str, start_lower: bool = False) -> str:
    """
    Converts a snake_case string to camelCase.
    The `start_lower` argument determines whether the first letter in the generated camelcase should
    be lowercase (if `start_lower` is True), or capitalized (if `start_lower` is False).
    """
    camel = snake.title()
    camel = re.sub("([0-9A-Za-z])_(?=[0-9A-Z])", lambda m: m.group(1), camel)
    if start_lower:
        camel = re.sub("(^_*[A-Z])", lambda m: m.group(1).lower(), camel)
    return camel


def alias(value: str) -> str:
    return snake2camel(value, start_lower=True)


class CamundaBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=alias)


class ExternalTask(CamundaBaseModel):
    activity_id: str
    activity_instance_id: str

    process_definition_id: str
    process_definition_key: str
    process_definition_version_tag: Optional[str] = None

    id: Optional[str] = None
    execution_id: Optional[str] = None
    process_instance_id: Optional[str] = None

    topic_name: str
    business_key: Optional[str] = None

    priority: int

    retries: Optional[int]

    worker_id: Optional[str]
    suspended: bool
    lock_expiration_time: Optional[datetime] = None

    error_message: Optional[str] = None

    # Not used with yio
    tenant_id: Optional[str] = None
