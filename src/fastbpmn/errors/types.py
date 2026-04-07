from pydantic import Field
from typing_extensions import Annotated

Retries = Annotated[int, Field(ge=0)]
RetryTimeout = Annotated[int, Field(ge=1000)]
