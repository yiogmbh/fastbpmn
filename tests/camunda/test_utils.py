import re
from typing import Optional, Tuple
from unittest.mock import MagicMock, PropertyMock

import pytest

from yio_minions.camunda.models import ExternalTask
from yio_minions.camunda.utils import (
    business_key_predicate,
    filter_predicate,
    topics_predicate,
)


@pytest.mark.parametrize(
    "business_key, pattern, expects_business_key_match",
    [
        pytest.param(None, "expeccts-this-key", False, id="No BusinessKey"),
        pytest.param(
            "exactly-this-key", "exactly-this-key", True, id="BusinessKey: Exact Match"
        ),
        pytest.param(
            "independent:suffix",
            "^independent:.*$",
            True,
            id="BusinessKey: Match Prefix",
        ),
        pytest.param(
            "some_weird-key-SuffixOnly",
            "^.*-SuffixOnly",
            True,
            id="BusinessKey: Match Suffix",
        ),
        pytest.param(
            "some_weird-key-suffixonly",
            "^.*-SuffixOnly",
            False,
            id="BusinessKey: NoMatch Suffix (invalid case)",
        ),
    ],
)
@pytest.mark.parametrize(
    "topic,topics,expects_topic_match",
    [
        pytest.param(
            "TopicA", None, True, id="No Topics to match"
        ),  # This case is usually not used ...
        pytest.param("TopicA", ("TopicB", "TopicA"), True, id="Topic: Match"),
        pytest.param("TopicA", ("TopicB", "TopicC"), False, id="Topic: NoMatch"),
    ],
)
def test_filter_predicate(
    topic: str,
    topics: Optional[Tuple[str, ...]],
    expects_topic_match: bool,
    business_key: Optional[str],
    pattern: Optional[str],
    expects_business_key_match: bool,
):
    predicate = filter_predicate(
        topics=topics, business_key_pattern=re.compile(pattern)
    )

    external_task = MagicMock(ExternalTask)
    type(external_task).business_key = PropertyMock(return_value=business_key)
    type(external_task).topic_name = PropertyMock(return_value=topic)

    matches = predicate(external_task)

    assert matches == (expects_topic_match and expects_business_key_match)


@pytest.mark.parametrize(
    "business_key, pattern, expects_match",
    [
        pytest.param(None, "expeccts-this-key", False, id="No BusinessKey"),
        pytest.param(
            "exactly-this-key", "exactly-this-key", True, id="BusinessKey: Exact Match"
        ),
        pytest.param(
            "independent:suffix",
            "^independent:.*$",
            True,
            id="BusinessKey: Match Prefix",
        ),
        pytest.param(
            "some_weird-key-SuffixOnly",
            "^.*-SuffixOnly",
            True,
            id="BusinessKey: Match Suffix",
        ),
        pytest.param(
            "some_weird-key-suffixonly",
            "^.*-SuffixOnly",
            False,
            id="BusinessKey: NoMatch Suffix (invalid case)",
        ),
    ],
)
def test_business_key_predicate(
    business_key: Optional[str], pattern: str, expects_match: bool
):

    predicate = business_key_predicate(business_key_pattern=re.compile(pattern))

    external_task = MagicMock(ExternalTask)
    type(external_task).business_key = PropertyMock(return_value=business_key)

    matches = predicate(external_task)

    assert matches == expects_match


@pytest.mark.parametrize(
    "topic,topics,expects_match",
    [
        pytest.param("TopicA", ("TopicB", "TopicA"), True, id="Topic: Match"),
        pytest.param("TopicA", ("TopicB", "TopicC"), False, id="Topic: NoMatch"),
    ],
)
def test_topic_predicate(topic: str, topics: Tuple[str, ...], expects_match):

    predicate = topics_predicate(topics=topics)

    external_task = MagicMock(ExternalTask)
    type(external_task).topic_name = PropertyMock(return_value=topic)

    matches = predicate(external_task)

    assert matches == expects_match
