from typing import Callable, List, Optional

from yio_minions.models import InputModel, OutputModel
from yio_minions.task import TaskHandler, TaskProperties
from yio_minions.utils.inspect import get_method_doc, get_method_name


class TaskGroup:
    """
    A Process indicates a bunch of external tasks belonging exactly to one Process
    """

    def __init__(
        self,
    ):
        self.task_props: List[TaskProperties] = []

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
        lock_duration: int = 300_000,  # defined in Task, shall we use it?
        retries: int = 4,
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
            topic=topic,
            handler=handler,
            title=title,
            tenants=tenants or None,
            process_definition_key=process_definition_key,
            description=description,
            input_class=input_class,
            output_class=output_class,
            lock_duration=lock_duration,
            retries=retries,
        )

        self.task_props.append(props)

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
        retries: int = 4,
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
