from pathlib import Path
from typing import Callable, List, Optional

from fastbpmn.models import InputModel, OutputModel
from fastbpmn.task import TaskHandler, TaskProperties
from fastbpmn.task_group import TaskGroup
from fastbpmn.utils.inspect import get_method_doc, get_method_name


class Process:
    """
    A Process indicates a bunch of external tasks belonging exactly to one Process
    """

    def __init__(
        self,
        title: str = None,
        description: str = None,
        tenants: str | list[str] | None = None,
        process_definition_key: str = None,
        bpmn_file: Optional[Path] = None,
    ):
        self.title = title or process_definition_key or "unnamed"
        self.description = description or ""

        if tenants and isinstance(tenants, str):
            tenants = [tenants]

        self._tenants = tenants or None
        self._process_definition_key = process_definition_key
        self.task_props: List[TaskProperties] = []
        self.bpmn_file = bpmn_file

    def add_taskgroup(self, task_group: TaskGroup) -> None:
        """
        Adds all tasks from the given Taskgroup to the actual Process
        :param task_group:
        :return:
        """
        topics = map(lambda x: x.topic, self.task_props)

        for task in task_group.task_props:
            if task.topic in topics:
                raise ValueError("Topic already added")

            self.task_props.append(
                TaskProperties(
                    process_definition_key=self._process_definition_key,
                    tenants=self._tenants,
                    **task.dict(exclude={"process_definition_key", "tenants"}),
                )
            )

    def add_task(
        self,
        topic: str,
        handler: TaskHandler,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        input_class: Optional[InputModel] = None,
        output_class: Optional[OutputModel] = None,
        lock_duration: int = 300_000,  # defined in Task, shall we use it?
        retries: int = 4,
    ):
        """
        Adding a task as specified to the Process
        """
        if not title:
            title = get_method_name(handler)
        if not description:
            description = get_method_doc(handler)

        props = TaskProperties(
            process_definition_key=self._process_definition_key,
            tenants=self._tenants,
            topic=topic,
            handler=handler,
            title=title,
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
    def process_definition_key(self):
        return self._process_definition_key
