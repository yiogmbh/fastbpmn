import importlib
import logging
from types import ModuleType

from aetpiref.typing import AETPIApplication

logger = logging.getLogger(__name__)


def as_module_and_variable(value: str) -> tuple[str, str]:
    """
    Parses a given string to extract the module name and variable name.

    Todo<dh>: We can add further validation here later.
    """
    if ":" not in value:
        value = f"{value}:minion"

    module_name, variable_name = value.split(":", maxsplit=1)

    return module_name, variable_name


def import_module(module_name: str) -> ModuleType:
    try:
        minion_module = importlib.import_module(module_name)
    except ImportError as exc:
        print(
            f"Probably, the MODULE_NAME={module_name} specified, does not exist.\n"
            "Please specify MODULE_NAME and VARIABLE_NAME variables to target your minion implementation."
        )
        raise exc
    return minion_module


def read_variable(module, variable_name: str) -> AETPIApplication:
    minion = getattr(module, variable_name, None)
    if minion is None:
        raise RuntimeError(
            f"The VARIABLE_NAME={variable_name} specified, does not exist.\n"
            "Please specify MODULE_NAME and VARIABLE_NAME variables to target your minion implementation."
        )

    # Todo<dh>: check if we can verify the variable being expected type
    return minion


def as_aetpi_application(value: str) -> AETPIApplication:

    module_name, variable_name = as_module_and_variable(value)

    module = import_module(module_name)

    return read_variable(module, variable_name)
