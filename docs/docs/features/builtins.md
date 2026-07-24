---

---
# Builtins

fastbpmn provides a set of builtins to use as depenedencies in your external task.

## ExternalTaskScope

Every external task execution runs within a scope (see [aetpi src](https://github.com/yiogmbh/aetpi/blob/main/src/aetpiref/typing.py#L51)). This scope defines the core properties of the execution.

To gather access to this data, simply use the `ExternalTaskScope` builtin and request it to be injected.

```python title="ExternalTaskScope" hl_lines="8 11 13 14"
from fastbpmn import Process
from aetpiref.typing import ExternalTaskScope

process_a = Process(process_definition_key="ProcessA")

@process_a.external_task("example")
async def context_example(
        scope: ExternalTaskScope # (1)!
) -> None:
    # check wehther the task is associated with a tenant or not
    tenant = scope["task"].get("tenant_id", None)  # (2)!

    if tenant and tenant != "tenant-a":
        raise Exception("This task is not associated with tenant-a")  # (3)!
```

1.  `scope` get injected automatically
2.  access the typed dict properties to gather the tenant
3.  raise an exception if the tenant is not `tenant-a`

## ProcessInstance

Using the process instance builtin, you can access various information about the process instance.

- id (process instance)
- business key
- tenant id
- start / end time (altough the latter will be None usually)
- process definition id / name / key / version
- process definition key
- process definition version
- process instance id

```python title="ProcessInstance" hl_lines="10 13 15 16 18 19"
from datetime import datetime, timedelta

from fastbpmn import Process
from fastbpmn.params import ProcessInstance

process_a = Process(process_definition_key="ProcessA")

@process_a.external_task("example")
async def context_example(
        inst: ProcessInstance # (1)!
) -> None:
    # check wehther the task is associated with a tenant or not
    tenant = inst.tenant_id  # (2)!

    if tenant and tenant != "tenant-a":
        raise Exception("This task is not associated with tenant-a")  # (3)!

    if (datetime.now() - (inst.start_time or datetime.now())) > timedelta(days=1):  # (4)!
        raise Exception("Ui this is an old instance right")
```

1.  `inst` get injected automatically
2.  access the models property to get the tenant
3.  raise an exception if the tenant is not `tenant-a`
4.  raise an exception if the process instance is older than 1 day

## Context

fastbpmn provides a `Context` class that gives you a few useful tools when handling external tasks.

### file variable download

!!! warning "Use with caution"

    Despite its possible with the supported process engines to have files as process instance variables a general advice
    is to avoid whenever possible. Due to the fact that this variables have to be stored in blob columns, there size
    is limited and excessive use might impact its performance.

#### Download file manually

```python title="Context usage for file variables" hl_lines="8 11 12"
from fastbpmn import Process
from fastbpmn.context import Context, Delete
from fastbpmn.models import FileInfo

process_a = Process(process_definition_key="ProzessA")

@process_a.external_task("context-example")
async def context_example(
        ctx: Context # (1)!
) -> None:
    info = FileInfo(filename="my-tiny-file.txt", variable_name="tiny_file")  # !(2)
    file_path = ctx.download_file(file_info=info, flags=Delete.ALWAYS) # (3)!
    return
```

1.  `Context` get injected automatically
2.  the `FileInfo` configures which variable to download including the resulting file name.
3.  `file_path` is a `Path` variable pointing to the downloaded file

#### Download file with InputModel

```python title="Advanced usage for Files" hl_lines="12 13 15"
from fastbpmn import Process
from fastbpmn.context import Context, Delete
from fastbpmn.models import FileInfo, InputOutputModel

process_a = Process(process_definition_key="ProzessA")

class ContextExampleInputs(InputOutputModel):
    tiny_file: FileInfo

@process_a.external_task("context-example")
async def context_example(
        ctx: Context, # (1)!
        var: ContextExampleInputs  # (2)!
) -> None:
    file_path = ctx.download_file(file_info=var.tiny_file, flags=Delete.ALWAYS) # (3)!
    return
```

1.  `Context` get injected automatically
2.  on execution `var` gets populated with matching process instance variables (`tiny_file` is a process instance variable with file type).
3.  `file_path` is a `Path` variable pointing to the downloaded file (using the `FileInfo` from our `var` variable)

### temporary files / directories

Sometimes its necessary to deal with files / directories while handling an external task. Consider the example that you
might need to query files from various apis before processing them.

fastbpmn helps you to ensure that such files or directories are automatically deleted when the task is done.

```python title="Context usage in external tasks" hl_lines="8 11 12"
from fastbpmn import Process
from fastbpmn.context import Context, Delete

process_a = Process(process_definition_key="ProzessA")

@process_a.external_task("context-example")
async def context_example(
        ctx: Context # (1)!
) -> None:
    print("Hello from a Prozess A, I create a file that is not deleted ....")
    dir_path = ctx.temp_dir(flags=Delete.NEVER) # (2)!
    file_path = ctx.temp_file(flags=Delete.ALWAYS) # (3)!
    return
```

1.  `Context` get injected automatically
2.  creates a temporary directory that resides (on most operating systems at least until restart)
3.  creates a temporary file that is deleted whenever the external task ends


## (deprecated) TaskProperties

Very similar to the `ExternalTaskScope` builtin, but with less properties, and being a pydantic model
instead of a typed dict.

!!! danger "Deprecated"
    This builtin is deprecated and will be removed in the next major release.


context: Context
    task: Task
    process_instance: ProcessInstance
    task_properties: TaskProperties
    scope: ExternalTaskScope
