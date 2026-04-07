import json
import uuid
from decimal import Decimal
from enum import Enum
from typing import Optional
from unittest.mock import MagicMock

import pytest
from pydantic import Field

from fastbpmn.context import Context
from fastbpmn.models import BaseOutputModel, TaskComplete, camunda_loads, encode


@pytest.fixture()
def mocked_context():
    mocked_context = MagicMock(Context)
    yield mocked_context


class Pricing(BaseOutputModel):
    tenant: str = Field(...)
    pricing_version: str = Field(...)
    pricings: dict | None = Field(None)


def test_issue17():
    """
    This unit test should make sure, that an error as in issue 17 won't happen again
    """
    json_str = encode(
        value=TaskComplete(
            worker_id="mein-worker",
            variables=Pricing(tenant="alpha", pricing_version="p21.10.1"),
        )
    )

    assert (
        json_str
        == '{"workerId": "mein-worker", "variables": {"tenant": {"value": "alpha", "type": "String", "valueInfo": {}}, "pricing_version": {"value": "p21.10.1", "type": "String", "valueInfo": {}}}}'
    )


def test_nested_model():
    class PricingCategory(Enum):
        ACQUIRE = "acquire"
        OPERATE = "operate"
        CONSTRUCT = "construct"
        PREPARE = "prepare"

    class Pricing(BaseOutputModel):
        tenant: str = Field(...)
        pricing_version: str = Field(...)
        pricing_category: PricingCategory = Field(...)  # *** ENUM ***
        pricings: Optional[dict] = Field({})

    class OuterModel(BaseOutputModel):
        pricing: Pricing

    json_str = encode(
        value=TaskComplete(
            worker_id="mein-worker",
            variables=OuterModel(
                pricing=Pricing(
                    tenant="alpha",
                    pricing_category=PricingCategory.PREPARE,
                    pricing_version="p21.10.1",
                )
            ),
        )
    )

    model = OuterModel(
        **camunda_loads(mocked_context, json.loads(json_str)["variables"], task=None)
    )
    assert (
        json_str
        == '{"workerId": "mein-worker", "variables": {"pricing": {"value": "{\\"tenant\\": \\"alpha\\", \\"pricing_version\\": \\"p21.10.1\\", \\"pricing_category\\": \\"prepare\\", \\"pricings\\": {}}", "type": "Json", "valueInfo": {}}}}'
    )

    assert model.pricing.tenant == "alpha"
    assert model.pricing.pricing_category == PricingCategory.PREPARE
    assert model.pricing.pricing_version == "p21.10.1"


@pytest.mark.parametrize(
    "value, expected_result_json",
    [
        pytest.param(
            uuid.UUID("e6bf9032-2453-422e-9d64-25a8a30c37b0"),
            """
        {
            "workerId": "mein-worker",
            "variables": {
                "uuid_value": {"value": "e6bf9032-2453-422e-9d64-25a8a30c37b0", "type": "String", "valueInfo": {}},
                "uuid_str": {"value": "e6bf9032-2453-422e-9d64-25a8a30c37b0", "type": "String", "valueInfo": {}}
            }
        }
        """,
            id="UUID v4",
        )
    ],
)
def test_encode_uuid(value: uuid.UUID, expected_result_json: str):
    """
    This references the issue with encoding uuid values in OutputModels

    Addresses issue #35:

    Bei Verwendung einer UUID im OutputMOdel schmiert der ET ohne Fehler ab / wird dann einfach wiederholt.

    Skript: yiotex_prepare/external_task.py (Repo = yio-minions-construct)

    ```
    class OutputModel(BaseOutputModel):
        doc_id: str			# OK
        # doc_id: UUID		# NOK
        has_security: bool
        has_watermark: bool
        has_barcode: bool


    doc_id = UUID('01840163-a001-7ffd-a8b0-87441f21f7c8')
    return OutputModel(doc_id=str(doc_id), **cfg)	# OK
    # return OutputModel(doc_id=doc_id, **cfg)		# NOK
    ```
    """

    class OutputModel(BaseOutputModel):
        uuid_value: uuid.UUID
        uuid_str: str

    output_model = OutputModel(uuid_value=value, uuid_str=str(value))
    encoded_result = json.loads(
        encode(value=TaskComplete(worker_id="mein-worker", variables=output_model))
    )
    expected_result = json.loads(expected_result_json)

    assert encoded_result == expected_result


@pytest.mark.parametrize(
    "values, expected_result_json",
    [
        pytest.param(
            {"required": "denied"},
            """
        {
            "workerId": "mein-worker",
            "variables": {
                "required": {"value": "denied", "type": "String", "valueInfo": {}},
                "default_accept": {"value": "accepted", "type": "String", "valueInfo": {}}
            }
        }
        """,
            id="Required only",
        ),
        pytest.param(
            {"required": "accepted", "default_none": "denied"},
            """
        {
            "workerId": "mein-worker",
            "variables": {
                "required": {"value": "accepted", "type": "String", "valueInfo": {}},
                "default_accept": {"value": "accepted", "type": "String", "valueInfo": {}},
                "default_none": {"value": "denied", "type": "String", "valueInfo": {}}
            }
        }
        """,
            id="Override Default None",
        ),
        pytest.param(
            {
                "required": "accepted",
                "default_accept": "denied",
                "default_none": "denied",
            },
            """
        {
            "workerId": "mein-worker",
            "variables": {
                "required": {"value": "accepted", "type": "String", "valueInfo": {}},
                "default_accept": {"value": "denied", "type": "String", "valueInfo": {}},
                "default_none": {"value": "denied", "type": "String", "valueInfo": {}}
            }
        }
        """,
            id="All values",
        ),
    ],
)
def test_issue38(values: dict, expected_result_json: str):
    """
    Bei der Nutzung von default Werten im Output Model werden diese nicht zu Camunda geladen, wenn nicht explizit angegeben.

    Im ET ist die letzte Zeile bspw.


    ```
    ...
    return OutputModel(event=AcceptEvent(**this), sid_token='reserved')
    ```


    Das OutputModel ist wie folgt defineirt:


    ```
    class OutputModel(BaseOutputModel):

        event: AcceptEvent              # add further Event types later

        pid_token: InstanceToken = Field(InstanceToken.ACCEPTED)

        sid_token: SiteToken = Field(SiteToken.RESERVED)
    ```

    In Camunda sind dann die Variablen `event` und `sid_token`.
    Die Variable `pid_token` fehlt.
    """

    class TestEnum(Enum):
        ACCEPTED = "accepted"
        DENIED = "denied"

    class OutputModel(BaseOutputModel):
        required: TestEnum  # add further Event types later

        default_accept: TestEnum = Field(TestEnum.ACCEPTED)

        default_none: TestEnum = Field(None)

    # Make sure the model behaves as expected
    with pytest.raises(ValueError):
        OutputModel()
    # Create two test models to be encoded
    output_model = OutputModel(**values)
    encoded_json = json.loads(
        encode(TaskComplete(worker_id="mein-worker", variables=output_model))
    )

    expected_json = json.loads(expected_result_json)

    assert encoded_json == expected_json


def test_nested_dict_none(mocked_context):
    """
    This test should ensure, that in case of an Output Model with a nested dict
    None values get rendered as expected
    """
    value_dict = {"set": "hallo", "unset": None}

    class OutputModel(BaseOutputModel):
        values: dict

    json_str = encode(
        value=TaskComplete(
            worker_id="mein-worker", variables=OutputModel(values=value_dict)
        )
    )

    model = OutputModel(
        **camunda_loads(mocked_context, json.loads(json_str)["variables"], task=None)
    )
    assert (
        json_str
        == '{"workerId": "mein-worker", "variables": {"values": {"value": "{\\"set\\": \\"hallo\\", \\"unset\\": null}", "type": "Json", "valueInfo": {}}}}'
    )

    assert model.values == value_dict


def test_numbers_nested_and_unnested(mocked_context):

    class OutputModel(BaseOutputModel):
        number: float
        decimal: Decimal
        nested: dict

    variables = OutputModel(
        number=1.228,
        decimal=Decimal("19.129"),
        nested={"number": 1.228, "decimal": Decimal("19.129")},
    )

    json_str = encode(value=TaskComplete(worker_id="mein-worker", variables=variables))

    reloaded = camunda_loads(
        mocked_context, json.loads(json_str)["variables"], task=None
    )

    model = OutputModel(**reloaded)

    assert model == OutputModel.model_construct(
        **{
            "number": 1.228,
            "decimal": Decimal("19.129"),
            "nested": {"number": 1.228, "decimal": "19.129"},
        }
    )
