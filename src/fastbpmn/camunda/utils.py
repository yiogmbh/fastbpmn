from typing import Callable, Optional, Pattern, Tuple

from fastbpmn.camunda.models import ExternalTask


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
