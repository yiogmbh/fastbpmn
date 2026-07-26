from functools import lru_cache
from typing import Any, Callable, Optional, Pattern, Tuple, TypeVar, Type

from aetpiref.typing import MessageDeliveryRecipient, TaskScope
from pydantic import TypeAdapter
from pydantic.alias_generators import to_snake

from fastbpmn.camunda.models import ExternalTask


ResponseType = TypeVar("ResponseType")


@lru_cache(maxsize=5)
def get_adapter(model: Any) -> TypeAdapter:
    return TypeAdapter(model)


def _to_snake(data: dict | None) -> dict | None:
    return {to_snake(k): v for k, v in data.items()} if data is not None else None


def to_snake_dict(data: Any) -> Any:
    if isinstance(data, dict):
        return {to_snake(k): to_snake_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [to_snake_dict(item) for item in data]
    return data


def transform_and_validate(
    data: list | dict,
    model: Type[TypeVar],
) -> TypeVar:
    snaked = to_snake_dict(data)

    return get_adapter(model).validate_python(snaked)


def get_pending_tasks_response(response: list) -> list[TaskScope]:
    adapter = get_adapter(list[TaskScope])
    snaked = [_to_snake(task) for task in response]

    return adapter.validate_python(snaked)


def _message_delivery_recipient_type_transformer(value: str) -> str:
    return "itermediate_catch_event" if value == "Execution" else "start_event"


def correlate_message_response(response: list) -> list[MessageDeliveryRecipient]:
    """
    Custom transformation of the response from the camunda rest api into a suitable typed dict format
    """
    adapter = get_adapter(list[MessageDeliveryRecipient])
    proc_inst_transformer = _to_snake
    exec_transformer = _to_snake

    def item_transformer(value: dict) -> dict:
        return {
            "type": _message_delivery_recipient_type_transformer(value["resultType"]),
            "process_instance": proc_inst_transformer(
                value.get("processInstance", None)
            ),
            "execution": exec_transformer(value.get("execution", None)),
            "variables": value.get("variables", None),
        }

    transformed = [item_transformer(item) for item in response]

    return adapter.validate_python(transformed)


def filter_predicate(
    topics: Optional[Tuple[str, ...]] = None,
    business_key_pattern: Optional[Pattern] = None,
) -> Callable[[ExternalTask], bool]:
    """
    Creates a predicate matching method that can be used to filter a List of ExternalTasks for matching
    candidates.
    :param topics: A tuple of topics to match the external tasks topic against
    :param business_key_pattern: A regular expression pattern to match the business_key of an external task.
    :return: A predicate method that accepts an ExternalTask instance, returns True on Match, False otherwise
    """
    predicates = []

    if topics:
        predicates.append(topics_predicate(topics))

    if business_key_pattern:
        predicates.append(business_key_predicate(business_key_pattern))

    return lambda task: all((predicate(task) for predicate in predicates))


def topics_predicate(topics: Tuple[str, ...]) -> Callable[[ExternalTask], bool]:
    return lambda task: task.topic_name in topics


def business_key_predicate(
    business_key_pattern: Pattern,
) -> Callable[[ExternalTask], bool]:

    # As a business_key is optional, we have to check that beforehand. Otherwise, we might receive an exception
    def check_business_key(task: ExternalTask) -> bool:
        return (
            task.business_key is not None
            and business_key_pattern.fullmatch(task.business_key) is not None
        )

    return check_business_key
