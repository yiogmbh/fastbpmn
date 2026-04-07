import json
import logging
from typing import Dict

from pydantic import ValidationError

from ..context import Context
from ..errors import DatatypeNotSupported
from .types.camunda7 import CamundaVariables, read_variables

logger = logging.getLogger(__name__)


def camunda_loads(
    context: Context, variables: Dict[str, Dict[str, str]], task
) -> Dict[str, CamundaVariables]:
    """
    This method helps to decode the dictionary retrieved by camunda on fetch (e.g.)
    """
    context = {"task": task, "context": context}
    try:
        return read_variables(variables, context=context)
    except ValidationError as exc:
        raise DatatypeNotSupported(
            f"Unsupported DataTypes detected. \n\nErrors: \n{json.dumps(exc.errors(), indent=4)}"
        ) from exc
