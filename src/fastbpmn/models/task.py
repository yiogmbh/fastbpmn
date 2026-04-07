from typing import Optional

from pydantic import ConfigDict, Field, SerializeAsAny

from .base import BaseModel, BaseOutputModel
from .types import Retries, RetryTimeout


class TaskBaseModel(BaseModel):
    worker_id: str = Field(..., alias="workerId")
    variables: SerializeAsAny[BaseOutputModel | None] = Field(None)

    model_config = ConfigDict(populate_by_name=True)


class TaskComplete(TaskBaseModel):
    pass


class TaskFailure(TaskBaseModel):
    error_message: str = Field(
        ...,
        title="Error Message",
        description="An message indicating the reason of the failure.",
        alias="errorMessage",
    )
    error_details: Optional[str] = Field(
        None,
        title="Error Details",
        description="A detailed error description.",
        alias="errorDetails",
    )
    retries: Retries = Field(
        ...,
        title="Retries",
        description="A number of how often the task should be retried. Must be >= 0. "
        "If this is 0, an incident is created and the task cannot be fetched "
        "anymore unless the retries are increased again. The incident's "
        "message is set to the errorMessage parameter.",
    )
    retry_timeout: RetryTimeout = Field(
        ...,
        title="Retry Timeout",
        description="A timeout in milliseconds before the external task becomes available again for fetching. "
        "Must be >= 0.",
        alias="retryTimeout",
    )


class TaskBPMNError(TaskBaseModel):
    error_code: str = Field(
        ...,
        title="Error Code",
        description="An error code that indicates the predefined error. Is used to identify the BPMN error handler.",
        alias="errorCode",
    )
    error_message: str = Field(
        ...,
        title="Error Message",
        description="An message indicating the reason of the failure.",
        alias="errorMessage",
    )
