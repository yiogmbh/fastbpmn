---
# Dependencies

## pydantic models

fastbpmn uses the power and magic of pydantic to simplify the handling of process instance variables

```python
from typing import Annotated
from annotated_types import Gt

from fastbpmn import FastBPMN
from fastbpmn.camunda import ProcessEngine
from fastbpmn.models import InputOutputModel

app = FastBPMN(name="Bob")

class PersonData(InputOutputModel):
    name: str
    age: Annotated[int, Gt(0)]

class MovieData(InputOutputModel):
    movie: str
    fsk: Annotated[int, Gt(0)] | None


class MovieGrant(InputOutputModel):
    greeting: str
    granted: bool


@app.external_task(
    topic="movie-access",
)
async def movie_access(person: PersonData, movie: MovieData) -> MovieGrant:
    """
    Check if the person may look at the movie or not
    """
    granted = person.age >= (movie.fsk or 0)
    greeting = f"Hello {person.name}, you are allowed to watch {movie.movie}"

    return MovieGrant(granted=granted, greeting=greeting)
```

## dependencies

!!! note "sync / async"

    fasbpmn supports async and sync dependencies, the latter get executed in a thread pool to avoid blocking the event
    loop.


### functions

```python
from typing import Annotated
from annotated_types import Gt

from fastbpmn import FastBPMN
from fastbpmn.camunda import ProcessEngine
from fastbpmn.models import InputOutputModel
from fastbpmn.params import Depends

app = FastBPMN(name="Bob")

class PersonData(InputOutputModel):
    name: str
    age: Annotated[int, Gt(0)]

class MovieData(InputOutputModel):
    movie: str
    fsk: Annotated[int, Gt(0)] | None

# can be async as well
def fetch_movie_data(movie: str) -> MovieData:
    # query some system for the fsk value
    fsk = query_fsk_from_imdb(movie)
    return MovieData(movie=movie, fsk=fsk)

class MovieGrant(InputOutputModel):
    greeting: str
    granted: bool


@app.external_task(
    topic="movie-access",
)
async def movie_access(person: PersonData, movie: dict = Depends(fetch_movie_data)) -> MovieGrant:
    """
    Check if the person may look at the movie or not
    """
    granted = person.age >= (movie.fsk or 0)
    greeting = f"Hello {person.name}, you are allowed to watch {movie.movie}"

    return MovieGrant(granted=granted, greeting=greeting)
```

### generators (context manager)

You can also use generator functions as dependencies, e.g. to clean up after yourself.

```python
from typing import Annotated
from annotated_types import Gt

from fastbpmn import FastBPMN
from fastbpmn.camunda import ProcessEngine
from fastbpmn.models import InputOutputModel
from fastbpmn.params import Depends

app = FastBPMN(name="Bob")

# no @contextmanager decorator allowed
# the employee_id has to be present as process variable
async def employee_data(employee_id: str):
    async with your_db_client as db:
        employee = await db.select_employee(employee_id)
        yield employee

@app.external_task(
    topic="employee-pay",
)
async def movie_access(employee: dict = Depends(employee_data)) -> None:
    """
    Check if the person may look at the movie or not
    """
    # perform employees payment

    return
    # once we exit this method the context manager gets closed



```
