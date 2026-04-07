# fastbpmn
A framework allowing to write external tasks for various bpmn process engines.

## Installation / Usage / Prerequisites

Ensure that the libmagic C library is installed on your system. See [python-magic](https://pypi.org/project/python-magic/) for installation on various systems.

On OSX use:
```
brew install libmagic
```

## Usage Example

```python
from yio_minions import YioMinion
from yio_minions.camunda import ProcessEngine
from yio_minions.models import BaseInputModel, BaseOutputModel

pe = ProcessEngine(process_key='order-process')
minion = YioMinion(process_engine=pe, name="Bob")

class OracleInput(BaseInputModel):
    string_variable: str        # Requires a process variable called string_variable
    integer_variable: int       # Requires a process variable called integer_variable

class OracleOutput(BaseOutputModel):
    win_or_loose: bool          # Sets the process variable win_or_loose in the end


@minion.external_task(
    topic="ask-oracle-delphi",
    input_class=OracleInput,
    output_class=OracleOutput,
)
async def ask_oracle_delphi(input_data: OracleInput):
    """
    External Task / DEMO
    Delphi was a sacred precinct that served as the seat of Pythia, the major oracle
    who was consulted about important decisions throughout the ancient classical world.
    """
    dummy_number = input_data.integer_variable + len(input_data.string_variable)

    win_or_loose = bool(dummy_number % 2)

    return OracleOutput(win_or_loose=win_or_loose)


@minion.external_task(
    topic="ask-oracle-dodona",
    input_class=OracleInput,
    output_class=OracleOutput,
)
async def ask_oracle_dodona(input_data: OracleInput):
    """
    External Task / DEMO
    Dodona in Epirus in northwestern Greece was the oldest Hellenic oracle.
    The earliest accounts in Homer describe Dodona as an oracle of Zeus.
    """
    dummy_number = input_data.integer_variable + len(input_data.string_variable)

    win_or_loose = not bool(dummy_number % 2)

    return OracleOutput(win_or_loose=win_or_loose)


# To start simply call the minion itself
# There are two commands supported by the bootstrapped command line interface
#   run      : Executes the minion and tries to work on external tasks
#   info     : Simply tells you something about the minions capabilities
if __name__ == '__main__':
    minion()
```

#### Startup/Shutdown Handler

```python
from yio_minions import YioMinion
from yio_minions.camunda import ProcessEngine


def init_startup_handler() -> None:
    print("added on startup")

def init_shutdown_handler() -> None:
    print("added on shutdown")

# 1. append on initialization
pe = ProcessEngine(process_key='order-process')
minion = YioMinion(
    process_engine=pe,
    name="Bob",
    on_startup=[init_startup_handler],
    on_shutdown=[init_shutdown_handler]
)

# 2. Use decorator approach to add your handlers
@minion.on_event("startup")
def decorator_startup_handler() -> None:
    print("Hello I'm a startup handler.")


@minion.on_event("shutdown")
async def decorator_shutdown_handler() -> None:
    print("Hello I'm a shutdown handler.")

# 3. Use a method already defined and append to the minion
async def already_existing_method():
    print("This method exists already and should be added to minion")

minion.add_event_handler("startup", already_existing_method)

```

#### Retries

In order to handle errors with retries there is a special exception that should be
raised within your external tasks. The latter example shows the usage:

```python
from yio_minions import YioMinion
from yio_minions.errors import RetryExternalTask
from yio_minions.camunda import ProcessEngine

pe = ProcessEngine(process_key='order-process')
minion = YioMinion(
    process_engine=pe,
    name="Bob"
)


@minion.external_task(
    topic="last-forever",
    input_class=None,
    output_class=None,
)
async def retry_infinite(input_data: None) -> None:

    print("I will last forever")
    raise RetryExternalTask(retries=1)  # No matter what happens we always tell the
                                        # process engine to try once again ;-)


@minion.external_task(
    topic="try-5times",
    input_class=None,
    output_class=None,
    retries=5
)
async def retry_infinite(input_data: None) -> None:

    print("You should see me 5 or 6 times ...")
    raise RetryExternalTask()   # not specifying a number of retries within the
                                # exception leads to decrease of initial number
```

#### No Input Values

It's possible to omit all the arguments if your external-task won't depend on input data.

```python
from yio_minions import YioMinion
from yio_minions.camunda import ProcessEngine

pe = ProcessEngine(process_key='order-process')
minion = YioMinion(
    process_engine=pe,
    name="Bob"
)


@minion.external_task(
    topic="without-args"
)
async def no_args() -> None:
    print("I'm almighty, I won't need any arguments. I will work anyway")
    return
```

#### Task/TaskProperties

Sometimes you might be interested in properties of the current Task or the TaskProperties in general.
You can declare an external task such that you will receive this objects for usage:

> **Attention** This is highly experimental and due to upcoming refactorings of the process engine interface the
> Task and TaskProperties Class are likely to change in the future.

```python
from yio_minions import YioMinion
from yio_minions.task import Task, TaskProperties
from yio_minions.camunda import ProcessEngine

pe = ProcessEngine(process_key='order-process')
minion = YioMinion(
    process_engine=pe,
    name="Bob"
)

@minion.external_task(
    topic="task-info",
    input_class=None,
    output_class=None,
)
async def print_taskinfo(input_data: None, task: Task, task_properties: TaskProperties) -> None:
    print(f"TaskId: {task.task_id} - initial retries: {task_properties.retries}")
    return
```

#### Process

A Process is a useful Method to create more structured code.

```python
from yio_minions import YioMinion, Process
from yio_minions.task import Task, TaskProperties
from yio_minions.camunda import ProcessEngine

pe = ProcessEngine()
minion = YioMinion(
    process_engine=pe,
    name="Bob"
)

process_a = Process(
    process_definition_key="ProzessA"
)

@process_a.external_task("print_a")
async def print_a(input_data: None) -> None:
    print("Hello from a Prozess A Only Task.")
    return


# put me in a different file if you want ;-)
process_b = Process(
    process_definition_key="ProzessB"
)

@process_b.external_task("print_b")
async def print_b(input_data: None) -> None:
    print("Hello from a Prozess B Only Task.")
    return


# You can also attach a TaskHandler method to multiple Processes

async def print_common(input_data: None, task: Task, task_properties: TaskProperties) -> None:
    print(f"Hello from a common task, i was executed by process ... {task.process_key}.")
    return


# Add the print common to processes wherever you like
# >-> The Topic can be different as well..
process_b.add_task("print_common", handler=print_common)
process_a.add_task("print_common", handler=print_common)


```

#### Context

You can make use of a context within your external task. The context provides some useful features
(e.g. create of temporary files / directories).

```python
from yio_minions import YioMinion, Process
from yio_minions.context import Context, Delete
from yio_minions.camunda import ProcessEngine

pe = ProcessEngine()
minion = YioMinion(
    process_engine=pe,
    name="Bob"
)

process_a = Process(
    process_definition_key="ProzessA"
)

@process_a.external_task("everlasting-file")
async def print_a(ctx: Context) -> None:
    print("Hello from a Prozess A, I create a file that is not deleted ....")
    file_path = ctx.temp_file(flags=Delete.NEVER)
    return

@process_a.external_task("deleted-file")
async def print_b(ctx: Context) -> None:
    print("Hello from a Prozess A, I create a file that deleted when I'm done ....")
    file_path = ctx.temp_file(flags=Delete.ALWAYS)
    return
```

#### File Handling

There are several ways to deal with File variables in Camunda. The following example shows three use cases.

The assumption is the following:

- the process has two file variables called `pdf_file_var` and `png_file_var` in camunda
- there is an external task that needs to work with these files
- the `png_file_var` is only optional and might not be present
- there are three scenarios:
    - the variable name in camunda are known
    - the variable names in camunda are subject to change, but there are two other variables
      holding the names (`pdf_file_var_name` and `png_file_var_name`)
    - the variable names in camunda are subject to change as is the number of files, but there is
      a list of variable names (`file_var_names`) that hold the names of the file variables

```python
import asyncio
from functools import cached_property

from pydantic import computed_field, model_validator

from yio_minions import YioMinion, Process
from yio_minions.context import Context
from yio_minions.camunda import ProcessEngine
from yio_minions.models import BaseInputModel, FileInfo, get_file_info_indirect

pe = ProcessEngine()
minion = YioMinion(
    process_engine=pe,
    name="Bob"
)

process_a = Process(
    process_definition_key="ProzessA"
)

pe = ProcessEngine(process_key='order-process')
minion = YioMinion(process_engine=pe, name="Bob")


class Option1InputModel(BaseInputModel):
    """
    This is the first option to deal with file variables.

    The variable names are known and can be used directly, that means there is a process
    variable called `pdf_file_var` and `png_file_var` in camunda with type file.
    """
    pdf_file_var: FileInfo
    png_file_var: FileInfo | None = None


class Option2InputModel(BaseInputModel):
    """
    This is the second option to deal with file variables.

    The variable names are not known and are subject to change. But there are two other
    variables (type string) that hold the names of the file variables.

    Be aware of the computed properties and validators that are used to ensure that the
    file variables are present as expected.
    """
    # if `pdf_file_var_name` is set to 'other_pdf_var' then a process variable called
    # `other_pdf_var` is expected to be present in camunda with type file. This variable
    # is then used to compute the value of the computed_field `pdf_file`.
    # if there is a process variable called pdf_file, then this variable is ignored (i guess)
    pdf_file_var_name: str
    png_file_var_name: str | None = None

    @computed_field
    @cached_property
    def pdf_file(self) -> FileInfo:
        return get_file_info_indirect(self, self.pdf_file_var, required=True)

    @computed_field
    @cached_property
    def png_file(self) -> FileInfo | None:
        return get_file_info_indirect(self, self.png_file_var, required=False)

    @model_validator(mode='after')
    def check_png_file(self):
        """
        Checks if the file_info is present at the given key
        """
        # this is a way to compute the value of the computed_field on initialization
        # to trigger validation immediately
        _ = self.png_file
        return self

    @model_validator(mode='after')
    def check_pdf_file(self):
        """
        Checks if the file_info is present at the given key
        """
        # this is a way to compute the value of the computed_field on initialization
        # to trigger validation immediately
        _ = self.pdf_file
        return self


class Option3InputModel(BaseInputModel):
    """
    This is the third option to deal with file variables.

    The variable names are not known and are subject to change. But there is a list of
    variable names (type string) that hold the names of the file variables.
    """
    file_var_names: list[str]

    @computed_field
    @cached_property
    def files(self) -> list[FileInfo]:
        return [get_file_info_indirect(self, file_var_name, required=True) for file_var_name in self.file_var_names]

    @model_validator(mode='after')
    def check_files(self):
        """
        Checks if the file_info is present at the given key
        """
        # this is a way to compute the value of the computed_field on initialization
        # to trigger validation immediately
        _ = self.files
        return self


@process_a.external_task("option1")
async def option1(ctx: Context, input_data: Option1InputModel) -> None:
    """
    This is the first option to deal with file variables.

    The variable names are known and can be used directly, that means there is a process
    variable called `pdf_file_var` and `png_file_var` in camunda with type file.
    """
    pdf_file = await ctx.download_file(input_data.pdf_file)
    if input_data.png_file:
        png_file = await ctx.download_file(input_data.png_file)
    # Or use gather ...

    # ... do something with the files ...
    return


@process_a.external_task("option2")
async def option2(ctx: Context, input_data: Option2InputModel) -> None:
    """
    This is the second option to deal with file variables.

    See that implementation of the external task is the same as with option 1,
    the difference is just that the variable names in camunda might differ as long
    as there are string variables telling you the names of the file variables.
    """
    pdf_file = await ctx.download_file(input_data.pdf_file)
    if input_data.png_file:
        png_file = await ctx.download_file(input_data.png_file)
    # Or use gather ...

    # ... do something with the files ...
    return


@process_a.external_task("option3")
async def option3(ctx: Context, input_data: Option3InputModel) -> None:
    """
    This is the third option to deal with file variables.

    See that implementation of the external task is the same as with option 1,
    the difference is just that the variable names in camunda might differ as long
    as there are string variables telling you the names of the file variables.
    """
    files = await asyncio.gather(*[ctx.download_file(file) for file in input_data.files])
    # ... do something with the files ... (the caveat is that you need to know the order and meaning of the files)
    # but there might be use cases where this won't matter).
    return

```



## Development

```shell
# setup evn ...
uv sync

# install commit hooks
prek install
```
