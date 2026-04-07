from typing import Awaitable, Callable

from aetpiref.typing import ExternalTaskScope

GuardHandler = Callable[[ExternalTaskScope], bool | Awaitable[bool]]
