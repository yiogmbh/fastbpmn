import dataclasses
import functools
from typing import Protocol

import structlog
from aetpiref.typing import TaskScope

from yio_minions.errors.base import DuplicateTaskHandlerError
from yio_minions.task import TaskProperties

logger = structlog.getLogger(__name__)


class Predicate:
    def __call__(self, task_scope: TaskScope) -> int:
        return 0

    def __or__(self, other: "Predicate") -> "Predicate":
        return AggregatePredicate(self, other)

    def __hash__(self) -> int:
        return hash(repr(self))


class AggregatePredicate(Predicate):
    def __init__(self, *predicates: Predicate) -> None:
        self.predicates = predicates

    def __call__(self, task_scope: TaskScope) -> int:
        return functools.reduce(
            lambda a, p: (a << 2) | p(task_scope), self.predicates, 0
        )

    def __eq__(self, other: Predicate) -> bool:
        if isinstance(other, AggregatePredicate):
            if len(self.predicates) != len(other.predicates):
                return False

            for idx, predicate in enumerate(self.predicates):
                if predicate != other.predicates[idx]:
                    return False

            return True

        return False

    def __or__(self, other: "Predicate") -> "Predicate":
        if isinstance(other, AggregatePredicate):
            return AggregatePredicate(*self.predicates, *other.predicates)
        return AggregatePredicate(*self.predicates, other)

    def __repr__(self) -> str:
        predicate_repr = " && ".join([repr(p) for p in self.predicates])

        return f"{predicate_repr}"

    def __hash__(self) -> int:
        return hash(repr(self))


class KeyPredicate(Predicate):
    def __init__(self, key: str, expected: str | list[str] | None = None) -> None:
        self.key = key

        if expected is None:
            self.expected = None
        elif isinstance(expected, str):
            self.expected = {expected}
        elif isinstance(expected, list | set):
            self.expected = set(expected)

    def __repr__(self):
        return f"({self.key}={self.expected or '*'})"

    def __hash__(self) -> int:
        return hash(repr(self))

    def __call__(self, task_scope: TaskScope) -> int:
        value = task_scope.get(self.key)
        match self.expected:
            case set():
                return int(value in self.expected) * 2
            case None:
                return 1

    def __eq__(self, other: Predicate) -> bool:
        if isinstance(other, KeyPredicate):
            return other.key == self.key and other.expected == self.expected
        return False


class TenantPredicate(KeyPredicate):
    def __init__(self, expected: str | list[str] | None = None) -> None:
        super().__init__("tenant_id", expected)


class ProcessDefinitionKeyPredicate(KeyPredicate):
    def __init__(self, expected: str | list[str] | None = None) -> None:
        super().__init__("process_definition_key", expected)


class TopicPredicate(KeyPredicate):
    def __init__(self, expected: str | list[str] | None = None) -> None:
        super().__init__("topic_name", expected)


def matcher(properties: TaskProperties) -> Predicate:

    predicate = (
        TenantPredicate(properties.tenants)
        | ProcessDefinitionKeyPredicate(properties.process_definition_key)
        | TopicPredicate(properties.topic)
    )
    logger.info(f"Match predicate: {predicate}", task_properties=properties)
    return predicate


@dataclasses.dataclass(frozen=True)
class Match:
    value: int
    properties: TaskProperties

    def __gt__(self, other: "Match") -> bool:
        return self.value > other.value

    def __eq__(self, other: "Match") -> bool:
        return self.value == other.value


class TaskMatcher(Protocol):
    def __call__(self, scope: TaskScope) -> TaskProperties | None: ...


def build_task_matcher(
    task_properties: list[TaskProperties],
) -> TaskMatcher:

    # a new way
    matchers = {}
    duplicate_errors = []

    for p in task_properties:
        m = matcher(p)
        if m in matchers:
            duplicate_errors.append(
                DuplicateTaskHandlerError(repr(m), matchers[m].handler, p.handler)
            )
            continue
        matchers[m] = p

    if duplicate_errors:
        raise ExceptionGroup(
            "One or more duplicate task handlers were found", duplicate_errors
        )

    def matching_func(scope: TaskScope) -> TaskProperties | None:

        matches = sorted(
            (Match(value, p) for m, p in matchers.items() if (value := m(scope))),
            reverse=True,
        )

        if not matches:
            return None

        if len(matches) > 1:
            logger.debug("Multiple matches", matches=matches)

        return matches[0].properties

    return matching_func
