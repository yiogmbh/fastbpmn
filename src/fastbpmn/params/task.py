from pydantic import BaseModel


class Task(BaseModel):
    id: str | None = None

    activity_id: str | None = None
    activity_instance_id: str | None = None

    execution_id: str | None = None
    error_message: str | None = None

    business_key: str | None = None
    topic_name: str | None = None

    process_definition_id: str | None = None
    process_definition_key: str | None = None
    process_definition_version_tag: str | None = None
    process_instance_id: str | None = None

    tenant_id: str | None = None

    retries: int | None = None

    suspended: bool | None = None

    priority: int | None = None

    worker_id: str | None = None

    # task properties related
    retry_timeout: int | None = None
    lock_duration: int | None = None
    title: str | None = None
    description: str | None = None
