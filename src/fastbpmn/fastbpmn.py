import inspect
import traceback
import warnings
from contextlib import asynccontextmanager
from itertools import chain
from typing import Any, Callable, List, Optional, Pattern, Sequence

import structlog
from aetpiref.typing import (
    AETPIApplication,
    AETPIReceiveCallable,
    AETPISendCallable,
    ExternalTaskScope,
    LifespanScope,
)

# import icecream
from rich import print  # pylint: disable=redefined-builtin

from fastbpmn.processor import ExternalTaskProcessor

from .lifespan import DeprecatedLifespan, NoopLifespan, _wrap_gen_lifespan_context
from .middleware import Middleware, P, _MiddlewareFactory
from .middleware.context import ContextMiddleware
from .middleware.exceptions import (
    ExceptionHandler,
    ExceptionHandlers,
    ExceptionMiddleware,
    ServerErrorMiddleware,
)
from .models import InputModel, OutputModel
from .process import Process
from .task import TaskHandler, TaskProperties
from ._types import AppType, DecoratedCallable, Lifespan
from .utils.inspect import get_method_doc, get_method_name
from .utils.names import get_random_name

logger = structlog.get_logger(__name__)


class FastBPMN:
    """
    The base class to handle external tasks later on
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        *,
        name: str | None = None,
        middleware: Sequence[Middleware] | None = None,
        exception_handlers: ExceptionHandlers = None,
        lifespan: Lifespan[AppType] | None = None,
        business_key_alike: Optional[Pattern] = None,
        wait_time: int = 10,
        probe_interval: int = 10,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
    ):
        """
        Creates a TaskMinion
        :param name: The minion name as str.
        :param wait_time: The number of seconds to wait if there is nothing to do at a given time (default: 10s)
        :param probe_interval: The interval in seconds in which the minion should trigger aliveness (default: 60s)
        :param on_startup: A list of startup methods to be invoked on minion start
        :param on_shutdown: A list of shutdown methods to be invoked on minion stop
        """
        self._task_props: List[TaskProperties] = []
        self.processes: List[Process] = []
        self.name = name or get_random_name()

        self._is_active = False

        self.exception_handlers = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: AETPIApplication | None = None

        if lifespan and (on_startup or on_shutdown):
            raise RuntimeError(
                "Using both lifespan and on_startup / on_shutdown is forbidden"
            )

        if lifespan is None and (on_startup or on_shutdown):
            self.lifespan_context = DeprecatedLifespan(self, on_startup, on_shutdown)
        elif lifespan is None:
            self.lifespan_context: Lifespan[Any] = NoopLifespan(self)

        elif inspect.isasyncgenfunction(lifespan):
            warnings.warn(
                "async generator function lifespans are deprecated, "
                "use an @contextlib.asynccontextmanager function instead",
                DeprecationWarning,
            )
            self.lifespan_context = asynccontextmanager(lifespan)
        elif inspect.isgeneratorfunction(lifespan):
            warnings.warn(
                "generator function lifespans are deprecated, use an @contextlib.asynccontextmanager function instead",
                DeprecationWarning,
            )
            self.lifespan_context = _wrap_gen_lifespan_context(lifespan)
        else:
            self.lifespan_context = lifespan

    def build_middleware_stack(self) -> AETPIApplication:
        error_handler = None
        exception_handlers: dict[Any, ExceptionHandler] = {}

        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                _error_handler = value
            else:
                exception_handlers[key] = value

        middleware = (
            [Middleware(ServerErrorMiddleware, handler=error_handler)]
            + self.user_middleware
            + [
                Middleware(
                    ExceptionMiddleware, handlers=exception_handlers
                ),  # , debug=debug)]
                Middleware(ContextMiddleware),
            ]
        )

        app = ExternalTaskProcessor(task_properties=self.task_props)
        for cls, args, kwargs in reversed(middleware):
            app = cls(app, *args, **kwargs)
        return app

    async def lifespan(
        self,
        scope: LifespanScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        """
        Handle ASGI lifespan messages, which allows us to manage application
        startup and shutdown events.
        """
        started = False
        app: Any = scope.get("app")
        await receive()
        try:
            async with self.lifespan_context(app) as maybe_state:
                if maybe_state is not None:
                    if "state" not in scope:
                        raise RuntimeError(
                            'The server does not support "state" in the lifespan scope.'
                        )
                    scope["state"].update(maybe_state)
                await send({"type": "lifespan.startup.complete"})
                started = True
                await receive()
        except BaseException:
            exc_text = traceback.format_exc()
            if started:
                await send({"type": "lifespan.shutdown.failed", "message": exc_text})
            else:
                await send({"type": "lifespan.startup.failed", "message": exc_text})
            raise
        else:
            await send({"type": "lifespan.shutdown.complete"})

    async def __call__(
        self,
        scope: ExternalTaskScope | LifespanScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        scope["app"] = self

        if scope["type"] == "lifespan":
            await self.lifespan(scope, receive, send)
            return

        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, receive, send)

    def on_event(self, event_type: str) -> Callable:  # pragma: nocover
        def decorator(func: Callable) -> Callable:
            self.add_event_handler(event_type, func)
            return func

        return decorator

    def add_event_handler(
        self, event_type: str, func: Callable
    ) -> None:  # pragma: no cover
        assert event_type in ("startup", "shutdown")

        if event_type == "startup":
            self.on_startup.append(func)
        else:
            self.on_shutdown.append(func)

    def include_process(self, process: Process) -> None:
        """
        Includes a bunch of external tasks all related to one specific process.
        """
        self.processes.append(process)

    @property
    def task_props_without_processes(self):
        return self._task_props

    @property
    def task_props(self) -> List[TaskProperties]:
        return self._task_props + list(chain(*[p.task_props for p in self.processes]))

    def add_exception_handler(
        self,
        exc_class: type[Exception],
        handler: ExceptionHandler,
    ) -> None:  # pragma: no cover
        self.exception_handlers[exc_class] = handler

    def exception_handler(
        self, exc_class: type[Exception]
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:

        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_exception_handler(exc_class, func)
            return func

        return decorator

    def add_middleware(
        self, middleware_class: _MiddlewareFactory[P], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        if self.middleware_stack is not None:  # pragma: no cover
            raise RuntimeError("Cannot add middleware after an application has started")
        self.user_middleware.insert(0, Middleware(middleware_class, *args, **kwargs))

    def add_task(
        self,
        topic: str,
        handler: TaskHandler,
        *,
        process_definition_key: str | None = None,
        tenants: str | list[str] | None = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        input_class: Optional[InputModel] = None,
        output_class: Optional[OutputModel] = None,
        lock_duration: int = 300_000,
        retries: int = 3,
    ):
        """
        Adding a task as specified to the minion
        """
        if not title:
            title = get_method_name(handler)
        if not description:
            description = get_method_doc(handler)

        if tenants and isinstance(tenants, str):
            tenants = [tenants]

        props = TaskProperties(
            tenants=tenants or None,
            process_definition_key=process_definition_key,
            topic=topic,
            handler=handler,
            title=title,
            description=description,
            input_class=input_class,
            output_class=output_class,
            lock_duration=lock_duration,
            retries=retries,
        )

        self._task_props.append(props)

    def external_task(
        self,
        topic: str,
        *,
        process_definition_key: str | None = None,
        tenants: str | list[str] | None = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        input_class: Optional[InputModel] = None,
        output_class: Optional[OutputModel] = None,
        lock_duration: int = 300_000,
        retries: int = 3,
    ) -> Callable[[TaskHandler], TaskHandler]:
        """
        Decorate a function to mark it as a task executor for the given topic. Variables or lock durations
        might be specified as required.
        """

        def decorator(func: TaskHandler) -> TaskHandler:

            self.add_task(
                topic=topic,
                handler=func,
                title=title,
                tenants=tenants,
                process_definition_key=process_definition_key,
                description=description,
                input_class=input_class,
                output_class=output_class,
                lock_duration=lock_duration,
                retries=retries,
            )
            # Just pass out the given handler (we just need the task handler for proper registration)
            return func

        return decorator

    @property
    def is_active(self) -> bool:
        return self._is_active

    def info(self):
        """
        A method to print out information about the minion
        """
        print(f"Minion: [bold yellow]{self.name}[/bold yellow]")

        for process in {task.process_definition_key for task in self.task_props}:
            known_topics = [
                task.topic
                for task in self.task_props
                if task.process_definition_key == process
            ]
            print(f"Process: {process} - Topics: {', '.join(known_topics)}")

    async def run(self) -> int:
        """
        Definition of an endless loop that is used to process the external tasks registered
        """
        raise NotImplementedError("""

 ------- NOT IMPLEMENTED ANYMORE -------

 Please refactor your code to use a e.g.
 a Camunda7Server implementation as a
 runner for your minions app

        """)

        return 0
