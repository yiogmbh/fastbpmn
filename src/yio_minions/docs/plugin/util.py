from pathlib import Path
from typing import TYPE_CHECKING, Tuple

from jsonschema2md2 import Parser
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File
from mkdocs.structure.pages import Page
from pydantic.v1 import BaseModel

if TYPE_CHECKING:
    from yio_minions import Process
    from yio_minions.task import TaskProperties


def task_property_table(task_props: "TaskProperties") -> str:
    """
    Creates a well formatted markdown table suitable to describe all task properties.
    """

    table = f"""
## Properties

| Property      | Value                         |
| ------------- | ----------------------------- |
| Topic         | {task_props.topic}            |
| Retries       | {task_props.retries}          |
| Retry Timeout | {task_props.retry_timeout} ms |
| Lock Duration | {task_props.lock_duration} ms |
        """
    return table


def process_index(
    process: "Process", process_dir: Path, *, config: MkDocsConfig
) -> Tuple[Page, File]:
    """
    Creates the markdown index page to be used as a process description page
    - Shows the bpmn if available
    - Heading
    - Short Description
    - Long Description
    """
    content = f"""
# {process.title}

{process.description}

    """

    if process.bpmn_file:
        bpmn_xml = process.bpmn_file.read_text(encoding="utf-8")

        content = f"""
{content}

## BPMN Diagramm

```{{.bpmn}}
{bpmn_xml}
```

        """
    docs_dir: Path = Path(config["docs_dir"])

    output_file = process_dir.joinpath("index.md")
    output_file.parent.mkdir(exist_ok=True, parents=True)
    output_file.write_text(content)

    file = File(
        output_file.relative_to(docs_dir).as_posix(),
        config["docs_dir"],
        config["site_dir"],
        config["use_directory_urls"],
    )
    page = Page(None, file, config)

    return page, file


def increase_hierarchy(text: str, level: int = 1) -> str:
    """
    Increase hierarchy level by given level.
    Example:
    # title -> ## title

    :param text: text to parse
    :param level: levels to add
    :return:
    """

    level_str = "#" * level
    lines = [
        level_str + line if line.startswith("#") else line for line in text.split("\n")
    ]
    return "\n".join(lines)


def model_as_md(model: BaseModel) -> str:
    """
    Converts the given Pydantic model (or the schema) to it's corresponding markdown representation.
    """

    if model is None:
        return ""

    parser = Parser(
        examples_as_yaml=False,
        show_examples="all",
    )

    text = "".join(parser.parse_schema(model.schema(by_alias=True)))

    return increase_hierarchy(text, 2)


def input_model(model: BaseModel) -> str:
    """Show input model, handle None Input"""

    text = "## Input\n\n"
    if not model:
        return text + "External task does not require a process instance variables."

    return (
        text
        + f"> External task expects the latter data as an input.\n\n{model_as_md(model)}"
    )


def output_model(model: BaseModel) -> str:
    """Show output model, handle None Output"""

    text = "## Output\n\n"
    if not model:
        return (
            text
            + "External task does not add or modify the process instance variables."
        )

    return (
        text
        + f"> The external task generates the latter data as an output.\n\n{model_as_md(model)}"
    )


def build_file(
    task: "TaskProperties", *, file_dir: Path, config: MkDocsConfig
) -> Tuple[Page, File]:
    """
    Create a markdown file for the given TaskProperties element.
    """
    test_content = f"""
# {task.title}

{task.description}

{task_property_table(task_props=task)}

{input_model(task.input_class)}

{output_model(task.output_class)}

    """
    docs_dir: Path = Path(config["docs_dir"])

    output_file = file_dir.joinpath(f"{task.topic}.md")
    output_file.parent.mkdir(exist_ok=True, parents=True)
    output_file.write_text(test_content)

    file = File(
        output_file.relative_to(docs_dir).as_posix(),
        config["docs_dir"],
        config["site_dir"],
        config["use_directory_urls"],
    )
    page = Page(task.title, file, config)

    return page, file
