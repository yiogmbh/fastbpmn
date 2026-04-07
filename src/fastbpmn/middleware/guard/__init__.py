from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPISendCallable,
    ExternalTaskScope,
)

from .types import GuardHandler
from .utils import wrap_app_with_guard

__all__ = ("GuardHandler", "GuardMiddleware")


class GuardMiddleware:
    """
    A suitable base middleware that can be used to implement a charon middleware.
    """

    def __init__(self, app: AETPIApplication, handler: GuardHandler):
        self.app = app
        self._handler = handler

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        if scope["type"] != "externaltask":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        await wrap_app_with_guard(self.app, self._handler)(scope, receive, send)
