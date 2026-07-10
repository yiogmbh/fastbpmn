---
# Context

fastbpmn provides a `Context` class that gives you a few useful tools when handling external tasks.

## file variable download

!!! warning "Use with caution"

    Despite its possible with the supported process engines to have files as process instance variables a general advice
    is to avoid whenever possible. Due to the fact that this variables have to be stored in blob columns, there size
    is limited and excessive use might impact its performance.

### Download file manually

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

### Download file with InputModel

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

## temporary files / directories

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
