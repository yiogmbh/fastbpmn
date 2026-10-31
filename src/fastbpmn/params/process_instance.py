from datetime import datetime, timedelta, timezone
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

    def duration(self, until: datetime | None = None) -> timedelta | None:
        """
        Get the elapsed time the process instance is running.

        Computation is between start_time and until (if until
        is not given then end_time is used else just now)

        ```python
        elapsed = start_time - (until or self.end_time or datetime.now(tz=timezone.utc))
        ```
        :param until:
        :return: The elapsed time as a timedelta object, or None if the start time is not available.
        """
        if self.start_time is None:
            return None

        end_time = until or self.end_time or datetime.now(tz=timezone.utc)

        return end_time - self.start_time
