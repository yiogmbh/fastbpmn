from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class ProcessInstance(BaseModel):
    id: str | None = None

    business_key: str | None = None

    start_time: datetime | None = None
    end_time: datetime | None = None

    process_definition_id: str | None = None
    process_definition_name: str | None = None
    process_definition_key: str | None = None
    process_definition_version: Annotated[
        str | None, Field(coerce_numbers_to_str=True)
    ] = None

    tenant_id: str | None = None
