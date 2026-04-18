from typing import Optional, Protocol, runtime_checkable

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from fastbpmn.params import Task
from .fastbpmn_types import LockDuration, TaskRetries, TaskTimeout
from .models import (
    InputModel,
    OutputModel,
)

__all__ = ["Task", "TaskProperties", "TaskHandler", "ExecuteTaskProperties"]


# Todo: consider implementing this protocol in a generic fashion to resolve issues
#       regarding type checking of the handler function.
@runtime_checkable
class TaskHandler(Protocol):
    """
    Complex method structures are easier to express as protocols.
    """

    def __call__(
        self, input_model: Optional[InputModel], task: Optional["Task"] = None
    ) -> Optional[OutputModel]: ...


class TaskProperties(BaseModel):
    def __eq__(self, *args, **kwargs):  # pylint: disable=useless-super-delegation
        super().__eq__(*args, **kwargs)

    process_definition_key: str | None = Field(
        None,
        title="Process Definition Key",
        description="The process definition key this task belongs to.",
    )

    # todo: add alias for topic_name
    topic: str = Field(
        ...,
        title="Topic",
        description="[REQUIRED] The topic for a task",
        validation_alias=AliasChoices("topic_name", "topic"),
    )

    lock_duration: LockDuration = Field(300_000, title="Lock Duration")

    handler: TaskHandler = Field(
        ...,
        title="Handler",
        description="[REQUIRED] The TaskHandler that is responsible to do the work.",
    )

    retries: TaskRetries = Field(
        3,
        title="Retries",
        description="The number of retries to be used for an external task (used if camunda exposes the task without"
        "retry definition).",
    )

    retry_timeout: TaskTimeout = Field(
        1000, title="Retry Timeout", description="Defines the timeout "
    )

    input_class: Optional[type[InputModel]] = None
    output_class: Optional[type[OutputModel]] = None

    title: Optional[str] = None
    description: Optional[str] = None

    tenants: list[str] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExecuteTaskProperties(TaskProperties):
    business_key: str = Field(
        ...,
        title="Business Key",
        description="[REQUIRED] The business key for the task to handle",
    )
