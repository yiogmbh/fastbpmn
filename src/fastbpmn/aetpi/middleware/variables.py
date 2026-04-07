"""
Middleware to handle variables in the AETPI
"""

from typing import TYPE_CHECKING, Any

from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPIReceiveEvent,
    AETPISendCallable,
    AETPISendEvent,
    ExternalTaskScope,
)

if TYPE_CHECKING:
    pass


class BaseSyncVariableHandlerMiddleware:
    """
    Base class for variable handlers
    """

    def __init__(self, app: AETPIApplication):
        self.app = app

    def process_application_variables(
        self, variables: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """
        Process variables, that are passed from the server to the application
        (from process engine -> to your task handlers)
        """
        return variables

    def process_server_variables(
        self, variables: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """
        Process variables, that are passed from the application to the server
        (from your task handlers -> to process engine)
        """
        return variables

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        if scope["type"] != "externaltask":  # pragma: no cover
            return await self.app(scope, receive, send)

        # Now lets see interest is only in the variable a like events
        # - exter

        async def receive_wrapper() -> AETPIReceiveEvent:

            event = await receive()

            match event:
                case {"type": "externaltask.execute.start", "variables": variables}:
                    variables = self.process_application_variables(variables)
                    event["variables"] = variables

            return event

        async def send_wrapper(event: AETPISendEvent) -> None:

            match event:
                case {"type": "externaltask.execute.complete", "variables": variables}:
                    variables = self.process_server_variables(variables)
                    event["variables"] = variables
                case {
                    "type": "externaltask.execute.failure",
                    "variables": variables,
                    "local_variables": local_variables,
                }:
                    variables = self.process_server_variables(variables)
                    local_variables = self.process_server_variables(local_variables)
                    event["variables"] = variables
                    event["local_variables"] = local_variables
                case {"type": "externaltask.execute.error", "variables": variables}:
                    variables = self.process_server_variables(variables)
                    event["variables"] = variables

            return await send(event)

        return await self.app(scope, receive_wrapper, send_wrapper)
