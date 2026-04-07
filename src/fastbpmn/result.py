from typing import Any

from aetpiref.typing import AETPIReceiveCallable, AETPISendCallable, ExternalTaskScope
from pydantic import BaseModel, TypeAdapter

from fastbpmn.aetpi import utils as eu
from fastbpmn.models import OutputModel

variable_encoder = TypeAdapter(dict[str, Any] | OutputModel | BaseModel | None)


def default_encoder(
    variables: dict[str, Any] | OutputModel | BaseModel | None,
) -> dict[str, Any] | None:
    return variable_encoder.dump_python(
        variables,
        by_alias=True,
        exclude_unset=False,
        exclude_none=True,  # Why? We should include defaults, as well as unset values but not None values?
    )


class ExternalTaskResult:
    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        pass


class SuccessResult(ExternalTaskResult):
    def __init__(
        self,
        variables: dict[str, Any] | OutputModel | None = None,
    ) -> None:
        self.variables = variables

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        variables = default_encoder(self.variables)
        await send(eu.create_event_execute_complete(variables=variables))


class AbortResult(ExternalTaskResult):
    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        await send(eu.create_event_execute_abort())


class BusinessErrorResult(ExternalTaskResult):
    def __init__(
        self,
        error_code: str | None = None,
        error_message: str | None = None,
        variables: dict[str, Any] | BaseModel | None = None,
    ):
        self.error_code = error_code
        self.error_message = error_message
        self.variables = variables

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:

        variables = default_encoder(self.variables)

        return await send(
            eu.create_event_execute_business_error(
                error_message=self.error_message,
                error_code=self.error_code,
                variables=variables,
            )
        )


class FailureResult(ExternalTaskResult):
    def __init__(
        self,
        error_message: str | None = None,
        error_details: str | None = None,
        retries: int | None = None,
        retry_timeout: int | None = None,
        variables: dict[str, Any] | BaseModel | None = None,
        local_variables: dict[str, Any] | BaseModel | None = None,
    ) -> None:
        self.error_message = error_message
        self.error_details = error_details
        self.retries = retries
        self.retry_timeout = retry_timeout
        self.variables = variables
        self.local_variables = local_variables

    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        variables = default_encoder(self.variables)
        local_variables = default_encoder(self.local_variables)

        return await send(
            eu.create_event_execute_failure(
                error_message=self.error_message,
                error_details=self.error_details,
                retries=self.retries,
                retry_timeout=self.retry_timeout,
                variables=variables,
                local_variables=local_variables,
            )
        )


class FatalFailureResult(FailureResult):
    def __init__(
        self,
        error_message: str | None = None,
        error_details: str | None = None,
        variables: dict[str, Any] | BaseModel | None = None,
        local_variables: dict[str, Any] | BaseModel | None = None,
    ) -> None:
        super().__init__(
            error_message=error_message,
            error_details=error_details,
            retries=0,
            retry_timeout=0,
            variables=variables,
            local_variables=local_variables,
        )


class RetryOnFailureResult(FailureResult):
    async def __call__(
        self,
        scope: ExternalTaskScope,
        receive: AETPIReceiveCallable,
        send: AETPISendCallable,
    ) -> None:
        task_scope = scope["task"]
        retries = self.retries or (task_scope.get("retries") - 1)

        return await send(
            eu.create_event_execute_failure(
                error_message=self.error_message,
                error_details=self.error_details,
                retries=retries,
                retry_timeout=self.retry_timeout,
            )
        )
