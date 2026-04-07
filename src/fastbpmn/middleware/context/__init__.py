from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPISendCallable,
    ExternalTaskScope,
)

from fastbpmn.context import Context


class ContextMiddleware:
    def __init__(self, app: AETPIApplication) -> None:
        self.app = app

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:

        if scope["type"] != "externaltask":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        file_downloader = scope["x_download_file_var"]

        async with Context(file_downloader) as context:
            scope["context"] = context

            await self.app(scope, receive, send)
