from dataclasses import InitVar, dataclass, field
from typing import Any, Dict, Set

ProcessDefinitionKeys = Set[str,]
TaskVariableNames = Set[str,]
TaskVariables = Dict[str, Any]


@dataclass
class TaskResponseType:
    variables: TaskVariables = field(default_factory=dict)
    delete_variables: TaskVariableNames = field(default_factory=set)
    is_complete: bool = field(default=False)

    def __post_init__(self):
        pass
        # self.variables = {} if self.variables is None else self.variables


@dataclass
class TaskCompleteType(TaskResponseType):
    # variables: dict = field(default_factory={})
    # delete_variables: Set[str]= field(default_factory=set)
    is_complete: bool = field(init=False, default=True)

    def __post_init__(self):
        pass


@dataclass
class ValueType:
    """
    Used to deserialize variables from camunda
    """

    obj: InitVar[dict]
    value: Any = field(init=False)
    type: str = field(init=False)
    info: Any = field(init=False)

    def __post_init__(self, obj):
        self.value = obj.get("value")
        self.type = obj.get("type").lower()
        self.info = obj.get("valueInfo")
