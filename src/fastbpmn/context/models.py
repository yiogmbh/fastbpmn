from dataclasses import dataclass
from typing import Any, Literal

from aetpiref.typing import NO_TENANT, TENANT_UNSPECIFIED
from pydantic import ConfigDict


@dataclass(frozen=True)
class Signal:
    signal_name: str
    variables: dict[str, Any] | None = None
    tenant_id: str | NO_TENANT | TENANT_UNSPECIFIED = TENANT_UNSPECIFIED


@dataclass(frozen=True)
class SignalResult:
    success: bool
    error_message: str | None = None


@dataclass(frozen=True)
class Message:
    message_name: str

    process_instance_id: str | None = None
    business_key: str | None = None
    tenant_id: str | NO_TENANT | TENANT_UNSPECIFIED | None = TENANT_UNSPECIFIED

    variables: dict[str, Any] | None = None
    local_variables: dict[str, Any] | None = None
    scoped_variables: dict[str, Any] | None = None

    multicast: bool = True


@dataclass(frozen=True)
class ProcessInstance:
    id: str
    definition_id: str
    business_key: str | None = None
    tenant_id: str | None = None


@dataclass(frozen=True)
class Execution:
    id: str
    process_instance_id: str
    tenant_id: str | None = None


@dataclass(frozen=True)
class MessageDeliveryRecipient:
    type: Literal["start_event", "itermediate_catch_event"]
    process_instance: ProcessInstance | None = None
    execution: Execution | None = None
    variables: dict[str, Any] | None = None


@dataclass(frozen=True)
class MessageResult:
    __pydantic_config__ = ConfigDict(extra="ignore")

    recipients: list[MessageDeliveryRecipient]


@dataclass(frozen=True)
class MessageFailure:
    error_message: str
