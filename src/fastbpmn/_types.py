from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from typing import Any, TypeVar

AppType = TypeVar("AppType")

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])

StatelessLifespan = Callable[[AppType], AbstractAsyncContextManager[None]]
StatefulLifespan = Callable[[AppType], AbstractAsyncContextManager[Mapping[str, Any]]]
Lifespan = StatelessLifespan[AppType] | StatefulLifespan[AppType]
