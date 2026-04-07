from pathlib import Path

from pydantic import Field
from typing_extensions import Annotated

Retries = Annotated[int, Field(ge=0)]
RetryTimeout = Annotated[int, Field(ge=0, multiple_of=500)]


CamundaPrimitives = bool | int | float | str
CamundaTypes = bool | int | float | str | Path
