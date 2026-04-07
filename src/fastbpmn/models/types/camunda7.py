from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Callable, Literal, Union

from pydantic import BaseModel, Field, Json, TypeAdapter, WrapValidator, field_validator
from pydantic_core.core_schema import ValidationInfo

from fastbpmn.models.base import FileInfo

if TYPE_CHECKING:
    from fastbpmn.task import Context, Task

BooleanTypeLiteral = Literal["boolean", "Boolean"]
IntegerTypeLiteral = Literal["integer", "Integer"]
ShortTypeLiteral = Literal["short", "Short"]
LongTypeLiteral = Literal["long", "Long"]
DoubleTypeLiteral = Literal["double", "Double"]
StringTypeLiteral = Literal["string", "String"]
JsonTypeLiteral = Literal["json", "Json"]
NullTypeLiteral = Literal["null", "Null"]
FileTypeLiteral = Literal["file", "File"]


def to_sync_callback(
    task: "Task", context: "Context", variable_name, pe_filename: str | None
) -> Callable[[], Path]:
    """
    Create a synchronous callback method that returns a path existing
    """

    def sync_callback() -> Path:

        filename = (
            context.temp_dir() / pe_filename if pe_filename else context.temp_file()
        )
        contents = task.file_variable_sync(variable_name)
        filename.write_bytes(contents)
        return filename

    return sync_callback


DecodedPythonTypes = Union[bool, int, float, str, None, Json, FileInfo]


class Camunda7Primitive(BaseModel):
    """
    Handling for primitive types
    """

    name: str
    value_type: str = Field(..., alias="type")
    value: DecodedPythonTypes


class Camunda7Boolean(Camunda7Primitive):
    """
    Handling for boolean values
    """

    name: str
    value_type: BooleanTypeLiteral = Field(..., alias="type")
    value: bool


class Camunda7Integer(Camunda7Primitive):
    """
    Handling for integer values
    """

    name: str
    value_type: IntegerTypeLiteral = Field(..., alias="type")
    value: int


class Camunda7Short(Camunda7Primitive):
    """
    Handling for short values
    """

    name: str
    value_type: ShortTypeLiteral = Field(..., alias="type")
    value: int


class Camunda7Long(Camunda7Primitive):
    """
    Handling for long values
    """

    name: str
    value_type: LongTypeLiteral = Field(..., alias="type")
    value: int


class Camunda7Double(Camunda7Primitive):
    """
    Handling for double values
    """

    name: str
    value_type: DoubleTypeLiteral = Field(..., alias="type")
    value: float


class Camunda7String(Camunda7Primitive):
    """
    Handling for string values
    """

    name: str
    value_type: StringTypeLiteral = Field(..., alias="type")
    # Check if = None is required as default assignment
    value: str | None


class Camunda7Json(Camunda7Primitive):
    """
    Handling for json values
    """

    name: str
    value_type: JsonTypeLiteral = Field(..., alias="type")
    value: Json


class Camunda7Null(Camunda7Primitive):
    """
    Handling for null values
    """

    name: str
    value_type: Literal["null", "Null"] = Field(..., alias="type")
    value: Any = None


class Camunda7FileInfo(Camunda7Primitive):
    """
    Handling for file values
    """

    name: str
    value_type: Literal["file", "File"] = Field(..., alias="type")
    value: FileInfo = Field(None, alias="valueInfo", validate_default=True)

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, value: dict[str, Any], info: ValidationInfo):

        value = value or {}

        context = info.context
        task: "Task" = context.get("task")
        task_context: "Context" = context.get("context")
        variable_name = info.data.get("name")
        sync_download = to_sync_callback(
            task, task_context, variable_name, value.get("filename")
        )
        return {**value, "variable_name": variable_name, "sync_download": sync_download}


# Annotated Union to parse single camunda7 variables
# easily
Camunda7VariableType = Union[
    Camunda7Boolean,
    Camunda7Integer,
    Camunda7Short,
    Camunda7Long,
    Camunda7Double,
    Camunda7String,
    Camunda7Json,
    Camunda7Null,
    Camunda7FileInfo,
]
AnnotatedCamunda7VariableType = Annotated[
    Union[
        Camunda7Boolean,
        Camunda7Integer,
        Camunda7Short,
        Camunda7Long,
        Camunda7Double,
        Camunda7String,
        Camunda7Json,
        Camunda7Null,
        Camunda7FileInfo,
    ],
    Field(discriminator="value_type"),
]


# We want / or need ... the variable name and value together
# so we need to list that somehow ...
Camunda7Variables = list[AnnotatedCamunda7VariableType]


def preprocess_var_dict(rest_vars: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Create a list that is suitable to be used with provided type adapter
    """
    return [{"name": key, **value} for (key, value) in rest_vars.items()]


# TypeAdapters useful for parsing camunda7 variables
Camunda7TypeAdapter = TypeAdapter(AnnotatedCamunda7VariableType)
Camunda7VariableAdapter = TypeAdapter(Camunda7Variables)  # Todo: Remove
Camunda7VariablesAdapter = TypeAdapter(Camunda7Variables)

# Conversion layer to more python friendly types
# for camunda7 variables
DecodedVariableTypes = Union[bool, int, float, str, dict, None, FileInfo]


def primitive_validator(
    v: Camunda7VariableType, handler, info: ValidationInfo
) -> DecodedVariableTypes:
    if isinstance(v, Camunda7VariableType):
        return v.value
    handler(v)


CamundaVariables = dict[
    str, Annotated[DecodedPythonTypes, WrapValidator(primitive_validator)]
]
CamundaVariableAdapter = TypeAdapter(CamundaVariables)


def read_variables(input: dict[str, Any], context: dict | None) -> CamundaVariables:
    """
    Read camunda variables from a dict
    """
    preprocessed = preprocess_var_dict(input)

    variables = Camunda7VariablesAdapter.validate_python(preprocessed, context=context)
    variables_dict = {v.name: v for v in variables}

    minion_variables = CamundaVariableAdapter.validate_python(variables_dict)

    return minion_variables
