import pytest
from aetpiref.typing import TaskScope
from assertpy import assert_that
from polyfactory.factories import TypedDictFactory

from fastbpmn.processor.routing import (
    AggregatePredicate,
    Predicate,
    ProcessDefinitionKeyPredicate,
    TenantPredicate,
    TopicPredicate,
)


class TaskScopeFactory(TypedDictFactory[TaskScope]): ...


class Given:
    @staticmethod
    def scope() -> TaskScope:
        return TaskScopeFactory.build()

    @staticmethod
    def scope_with(
        tenant: str | None = None,
        process_definition_key: str | None = None,
        topic_name: str | None = None,
    ) -> TaskScope:
        scope = Given.scope()

        scope["tenant_id"] = tenant

        scope["process_definition_key"] = process_definition_key

        scope["topic_name"] = topic_name

        return scope


class TestProcessDefinitionKeyPredicate:
    @pytest.mark.parametrize(
        "process_definition_key,expected_result",
        [
            pytest.param(None, 1, id="scope without tenant"),
            pytest.param("any", 1, id="scope with any tenant"),
        ],
    )
    def test_when_expected_process_definition_key_is_none_matches_always(
        self, process_definition_key: str | None, expected_result: int
    ):

        scope = Given.scope_with(process_definition_key=process_definition_key)
        predicate = ProcessDefinitionKeyPredicate(expected=None)

        result = predicate(scope)

        assert_that(result).is_not_none().is_equal_to(expected_result)

    @pytest.mark.parametrize(
        "expected_process_definition_key,process_definition_key,expected_result",
        [
            pytest.param("any", "any", 2, id="matching process_definition_key (=2)"),
            pytest.param(
                ["any", "other"],
                "other",
                2,
                id="one of multiple process_definition_key matching (=2)",
            ),
            pytest.param(
                ["any", "other"],
                "not",
                0,
                id="none of multiple process_definition_key matching (=0)",
            ),
            pytest.param(
                "any", "not", 0, id="process_definition_key not matching (=0)"
            ),
        ],
    )
    def test_when_expected_process_definition_key_given(
        self,
        expected_process_definition_key: str,
        process_definition_key: str,
        expected_result: int,
    ):
        scope = Given.scope_with(process_definition_key=process_definition_key)
        predicate = ProcessDefinitionKeyPredicate(
            expected=expected_process_definition_key
        )

        result = predicate(scope)

        assert_that(result).is_not_none().is_equal_to(expected_result)

    @pytest.mark.parametrize(
        "a,b,expected_result",
        [
            pytest.param("any", "any", True, id="same exected tenant"),
            pytest.param(None, None, True, id="same exected tenant (None)"),
            pytest.param(
                "any", ["any"], True, id="same exected tenant (value vs list)"
            ),
            pytest.param("any", "other", False, id="different tenant"),
            pytest.param(
                "any", ["other"], False, id="different tenant (value vs list)"
            ),
        ],
    )
    def test_when_expected_process_definition_key_equals_then_eq(
        self, a: str | None, b: str | None, expected_result: bool
    ):
        predicate_a = ProcessDefinitionKeyPredicate(expected=a)
        predicate_b = ProcessDefinitionKeyPredicate(expected=b)

        result = predicate_a == predicate_b
        assert_that(result).is_equal_to(expected_result)


class TestTenantPredicate:
    @pytest.mark.parametrize(
        "tenant,expected_result",
        [
            pytest.param(None, 1, id="scope without tenant"),
            pytest.param("any", 1, id="scope with any tenant"),
        ],
    )
    def test_when_expected_tenant_is_none_matches_always(
        self, tenant: str | None, expected_result: int
    ):
        scope = Given.scope_with(tenant=tenant)
        predicate = TenantPredicate(expected=None)

        result = predicate(scope)

        assert_that(result).is_not_none().is_equal_to(expected_result)

    @pytest.mark.parametrize(
        "expected_tenant,tenant,expected_result",
        [
            pytest.param("any", "any", 2, id="matching tenant (=2)"),
            pytest.param(
                ["any", "other"], "other", 2, id="one of multiple tenants matching (=2)"
            ),
            pytest.param(
                ["any", "other"], "not", 0, id="none of multiple tenants matching (=0)"
            ),
            pytest.param("any", "not", 0, id="tenant not matching (=0)"),
        ],
    )
    def test_when_expected_tenant_given(
        self, expected_tenant: str, tenant: str, expected_result: int
    ):
        scope = Given.scope_with(tenant=tenant)
        predicate = TenantPredicate(expected=expected_tenant)

        result = predicate(scope)

        assert_that(result).is_not_none().is_equal_to(expected_result)

    @pytest.mark.parametrize(
        "a,b,expected_result",
        [
            pytest.param("any", "any", True, id="same exected tenant"),
            pytest.param(None, None, True, id="same exected tenant (None)"),
            pytest.param(
                "any", ["any"], True, id="same exected tenant (value vs list)"
            ),
            pytest.param("any", "other", False, id="different tenant"),
            pytest.param(
                "any", ["other"], False, id="different tenant (value vs list)"
            ),
        ],
    )
    def test_when_expected_tenant_equals_then_eq(
        self, a: str | None, b: str | None, expected_result: bool
    ):
        predicate_a = TenantPredicate(expected=a)
        predicate_b = TenantPredicate(expected=b)

        result = predicate_a == predicate_b
        assert_that(result).is_equal_to(expected_result)


class TestTopicPredicate:
    @pytest.mark.parametrize(
        "tenant,expected_result",
        [
            pytest.param("any", 1, id="scope with any topic"),
        ],
    )
    def test_when_expected_topic_is_none_matches_always(
        self, tenant: str | None, expected_result: int
    ):
        scope = Given.scope_with(tenant=tenant)
        predicate = TopicPredicate(expected=None)

        result = predicate(scope)

        assert_that(result).is_not_none().is_equal_to(expected_result)

    @pytest.mark.parametrize(
        "expected_tenant,tenant,expected_result",
        [
            pytest.param("any", "any", 2, id="matching tenant (=2)"),
            pytest.param(
                ["any", "other"], "other", 2, id="one of multiple tenants matching (=2)"
            ),
            pytest.param(
                ["any", "other"], "not", 0, id="none of multiple tenants matching (=0)"
            ),
            pytest.param("any", "not", 0, id="tenant not matching (=0)"),
        ],
    )
    def test_when_expected_topic_given(
        self, expected_tenant: str, tenant: str, expected_result: int
    ):
        scope = Given.scope_with(tenant=tenant)
        predicate = TenantPredicate(expected=expected_tenant)

        result = predicate(scope)

        assert_that(result).is_not_none().is_equal_to(expected_result)

    @pytest.mark.parametrize(
        "a,b,expected_result",
        [
            pytest.param("any", "any", True, id="same expected topic"),
            pytest.param(None, None, True, id="same expected topic (None)"),
            pytest.param(
                "any", ["any"], True, id="same expected topic (value vs list)"
            ),
            pytest.param("any", "other", False, id="different topic"),
            pytest.param("any", ["other"], False, id="different topic (value vs list)"),
        ],
    )
    def test_when_expected_tenant_equals_then_eq(
        self, a: str | None, b: str | None, expected_result: bool
    ):
        predicate_a = TopicPredicate(expected=a)
        predicate_b = TopicPredicate(expected=b)

        result = predicate_a == predicate_b
        assert_that(result).is_equal_to(expected_result)


class TestAggregatePredicate:
    class FixPredicate(Predicate):
        def __init__(self, value: int) -> None:
            self.value = value

        def __call__(self, scope: TaskScope) -> int:
            return self.value

        def __repr__(self):
            return f" = {self.value}"

    @pytest.mark.parametrize(
        "values,expected_result",
        [
            pytest.param([0], 0, id="single predicate (0)"),
            pytest.param([1], 1, id="single predicate (1)"),
            pytest.param([2], 2, id="single predicate (2)"),
            pytest.param([0, 0], 0, id="two predicate (0)"),
            pytest.param([0, 1], 1, id="two predicate (1)"),
            pytest.param([0, 2], 2, id="two predicate (2)"),
            pytest.param([0, 1, 0], 4, id="three predicate (0,1,0)"),
            pytest.param([2, 0, 1], 33, id="three predicate (2,0,1)"),
            pytest.param([0, 2, 2], 10, id="three predicate (0,2,2)"),
        ],
    )
    def test_when_called_combines_predicate_results(
        self, values: list[int], expected_result: int
    ):
        predicates = [TestAggregatePredicate.FixPredicate(value) for value in values]
        aggregate = AggregatePredicate(*predicates)
        scope = Given.scope()

        result = aggregate(scope)

        assert_that(result).is_equal_to(expected_result)

    def test_when_combine_aggregate(self):

        predicates_a = [
            TestAggregatePredicate.FixPredicate(1),
            TestAggregatePredicate.FixPredicate(2),
        ]
        predicates_b = [
            TestAggregatePredicate.FixPredicate(3),
            TestAggregatePredicate.FixPredicate(4),
        ]
        aggregate_a = AggregatePredicate(*predicates_a)
        aggregate_b = AggregatePredicate(*predicates_b)
        aggregate_all = AggregatePredicate(*predicates_a, *predicates_b)

        combine = aggregate_a | aggregate_b

        assert_that(combine).is_equal_to(aggregate_all)
