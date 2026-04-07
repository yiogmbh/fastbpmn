from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from yio_minions.aetpi.middleware import BaseSyncVariableHandlerMiddleware

from .decoder import decode_variables
from .encoder import encode_variables


class Camunda7VariablePreprocessor(BaseSyncVariableHandlerMiddleware):
    """
    Middleware to preprocess variables before sending to the server
    """

    adapter = TypeAdapter(Any)

    def process_application_variables(
        self, variables: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """ "
        Process variables, that are passed from the server to the application
        (from process engine -> to your task handlers)
        """
        if variables is None:
            return None

        return decode_variables(variables)

    def process_server_variables(
        self, variables: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """
        Process variables, that are passed from the application to the server
        (from your task handlers -> to process engine)
        """
        if variables is None:
            return None

        for key, value in variables.items():
            match value:
                case Path():
                    # TODO: Add file handling
                    # We won't do anything with the Path object
                    continue
                case _:
                    variables[key] = self.adapter.dump_python(value, mode="json")

        return encode_variables(variables)
