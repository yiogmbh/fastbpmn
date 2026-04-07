from typing import Any, Awaitable, Callable

from aetpiref.typing import ExternalTaskScope

from fastbpmn.result import ExternalTaskResult

ExceptionHandler = Callable[
    [ExternalTaskScope, Exception], ExternalTaskResult | Awaitable[ExternalTaskResult]
]
ExceptionHandlers = dict[Any, ExceptionHandler]
