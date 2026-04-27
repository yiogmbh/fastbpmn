import uuid
from contextlib import AsyncExitStack
from typing import Any, Generator, AsyncGenerator
from unittest import mock

from aetpiref.typing import ExternalTaskScope
from typing_extensions import TypedDict

import pytest
from assertpy import assert_that
from pydantic import BaseModel, TypeAdapter

from fastbpmn.context import Context
from fastbpmn.dependencies.models import Dependant, Builtins, ResolvedDependant
from fastbpmn.dependencies.utils import build_dependant, resolve_dependencies
from fastbpmn.params import ProcessInstance, Task, Depends
from fastbpmn.task import TaskProperties


@pytest.fixture
def mocked_builtins() -> Generator[Builtins, Any, None]:

    yield {
        "context": mock.MagicMock(Context),
        "task": mock.MagicMock(Task),
        "process_instance": mock.MagicMock(ProcessInstance),
        "task_properties": mock.MagicMock(TaskProperties),
        "scope": mock.MagicMock(ExternalTaskScope),
    }


@pytest.fixture(scope="function")
async def exit_stack() -> AsyncGenerator[AsyncExitStack[bool | None], None]:

    async with AsyncExitStack() as stack:
        yield stack
        pass


class TestBuildDependant:
    @pytest.mark.parametrize(
        "builtin_type",
        [ProcessInstance, Task, TaskProperties, Context, ExternalTaskScope],
    )
    def test_builtins_without_annotations(self, builtin_type):
        def call(proc: builtin_type) -> None:
            pass

        dependant = build_dependant(call)

        assert_that(dependant).is_not_none().is_type_of(Dependant)
        assert_that(dependant.builtins).is_not_none().is_length(1)
        assert_that(dependant.builtins).extracting("name").contains("proc")
        # we cannot use extracting, cause apparently it instantiates the class ...
        assert_that(dependant.builtins[0].clazz).is_equal_to(builtin_type)

    def test_input_model_without_annotation(
        self,
    ):

        class InputModel(BaseModel):
            name: str

        async def call(var: InputModel) -> None:
            pass

        dependant = build_dependant(call)

        assert_that(dependant).is_not_none().is_type_of(Dependant)
        assert_that(dependant.input_models).is_not_none().is_length(1)
        assert_that(dependant.input_models).extracting("name").contains("var")
        assert_that(dependant.input_models[0].clazz).is_equal_to(InputModel)
        assert_that(dependant.input_models[0].adapter).is_not_none().is_type_of(
            TypeAdapter
        )

    def test_typed_dict_without_annotation(
        self,
    ):

        class InputDict(TypedDict, total=False):
            name: str

        async def call(var: InputDict) -> None:
            pass

        dependant = build_dependant(call)

        assert_that(dependant).is_not_none().is_type_of(Dependant)
        assert_that(dependant.input_models).is_not_none().is_length(1)
        assert_that(dependant.input_models).extracting("name").contains("var")
        assert_that(dependant.input_models[0].clazz).is_equal_to(InputDict)
        assert_that(dependant.input_models[0].adapter).is_not_none().is_type_of(
            TypeAdapter
        )

    @pytest.mark.parametrize(
        "some_variable_type",
        [
            uuid.UUID,
            str,
            float,
            int,
            bool,
        ],
    )
    def test_variable_dependant_without_annotation(self, some_variable_type):

        def call(var: some_variable_type) -> None:
            pass

        dependant = build_dependant(call)
        assert_that(dependant).is_not_none().is_type_of(Dependant)
        assert_that(dependant.input_variables).is_not_none().is_length(1)
        assert_that(dependant.input_variables).extracting("name").contains("var")
        assert_that(dependant.input_variables).extracting("alias").contains("var")
        assert_that(dependant.input_variables[0].clazz).is_equal_to(some_variable_type)
        assert_that(dependant.input_variables[0].adapter).is_not_none().is_type_of(
            TypeAdapter
        )

    def test_sub_dependency_without_annotation(
        self,
    ):

        def dep_call(var: uuid.UUID) -> str:
            return str(var)

        def call(dep: str = Depends(dep_call)) -> None:
            pass

        dependant = build_dependant(call)

        assert_that(dependant).is_not_none().is_type_of(Dependant)
        assert_that(dependant.sub_dependencies).is_not_none().is_length(1)

        sub_dependency = dependant.sub_dependencies[0]

        assert_that(sub_dependency).is_not_none().is_type_of(Dependant)
        assert_that(sub_dependency.input_variables).is_not_none().is_length(1)
        assert_that(sub_dependency.input_variables).extracting("name").contains("var")

    def test_mixed_dependencies_without_annotation(
        self,
    ):

        class InputModel(BaseModel):
            var: uuid.UUID

        def call(
            var: uuid.UUID, model: InputModel, b1: ProcessInstance, b2: Context
        ) -> None:
            pass

        dependant = build_dependant(call)

        assert_that(dependant).is_not_none().is_type_of(Dependant)
        assert_that(dependant.input_variables).is_not_none().is_length(1)
        assert_that(dependant.input_models).is_not_none().is_length(1)
        assert_that(dependant.builtins).is_not_none().is_length(2)


class TestResolveDependencies:
    @pytest.mark.asyncio
    async def test_builtins_only(
        self,
        mocked_builtins: Builtins,
        exit_stack: AsyncExitStack,
    ) -> None:

        def call(
            context: Context,
            task: Task,
            props: TaskProperties,
            proc: ProcessInstance,
            any_scope: ExternalTaskScope,
        ):
            pass

        expected_builtins = {
            "context": mocked_builtins["context"],
            "task": mocked_builtins["task"],
            "props": mocked_builtins["task_properties"],
            "proc": mocked_builtins["process_instance"],
            "any_scope": mocked_builtins["scope"],
        }

        dependant = build_dependant(call)
        resolved = await resolve_dependencies(
            dependant, variables={}, builtins=mocked_builtins, exit_stack=exit_stack
        )

        assert_that(resolved).is_not_none()
        assert_that(resolved.kwargs).is_not_none().contains_entry(**expected_builtins)

    @pytest.mark.parametrize(
        "passed_vars",
        [
            {"var": uuid.uuid4(), "greet": "hello"},
            {"var": uuid.uuid4(), "greet": "hello with age", "age": 42},
        ],
    )
    @pytest.mark.asyncio
    async def test_input_model_only(
        self, mocked_builtins: Builtins, exit_stack: AsyncExitStack, passed_vars: dict
    ) -> None:

        class TestModel(BaseModel):
            var: uuid.UUID
            greet: str
            age: int = 15

        def call(input_model: TestModel) -> None:
            pass

        dependant = build_dependant(call)

        dft_vars = {"age": 15}
        expected_vars = dft_vars | passed_vars

        resolved = await resolve_dependencies(
            dependant,
            variables=passed_vars,
            builtins=mocked_builtins,
            exit_stack=exit_stack,
        )

        assert_that(resolved).is_not_none().is_type_of(ResolvedDependant)

        assert_that(resolved.kwargs).contains_key("input_model")
        assert_that(resolved.kwargs["input_model"]).is_not_none().is_type_of(TestModel)
        assert_that(
            resolved.kwargs["input_model"].model_dump(mode="python")
        ).contains_entry(**expected_vars)

        # assert_that(resolved.kwargs).is_not_none().contains(
        #    "greet", "var", "age"
        # ).contains_entry(**expected_vars,)

    @pytest.mark.asyncio
    async def test_variable_only(
        self, mocked_builtins: Builtins, exit_stack: AsyncExitStack
    ) -> None:

        def call(var: uuid.UUID, greet: str, age: int = 15) -> None:
            pass

        dependant = build_dependant(call)

        passed_vars = {
            "var": uuid.uuid4(),
            "greet": "Hello World",
        }
        dft_vars = {"age": 15}

        resolved = await resolve_dependencies(
            dependant,
            variables=passed_vars,
            builtins=mocked_builtins,
            exit_stack=exit_stack,
        )

        assert_that(resolved).is_not_none().is_type_of(ResolvedDependant)
        assert_that(resolved.kwargs).is_not_none().contains(
            "greet", "var", "age"
        ).contains_entry(**passed_vars, **dft_vars)

    @pytest.mark.asyncio
    async def test_with_sub_dependency(
        self, mocked_builtins: Builtins, exit_stack: AsyncExitStack
    ) -> None:

        def sub_dep(var: uuid.UUID, greet: str, age: int = 15) -> dict:
            return {
                "var": var,
                "greet": greet,
                "age": age,
            }

        def call(sub: dict = Depends(sub_dep)) -> None:
            pass

        dependant = build_dependant(call)

        passed_vars = {
            "var": uuid.uuid4(),
            "greet": "Hello World",
        }
        dft_vars = {"age": 15}

        resolved = await resolve_dependencies(
            dependant,
            variables=passed_vars,
            builtins=mocked_builtins,
            exit_stack=exit_stack,
        )

        assert_that(resolved).is_not_none().is_type_of(ResolvedDependant)
        assert_that(resolved.kwargs).is_not_none().contains("sub")
        assert_that(resolved.kwargs["sub"]).contains_entry(**passed_vars, **dft_vars)

    @pytest.mark.asyncio
    async def test_with_async_sub_dependency(
        self, mocked_builtins: Builtins, exit_stack: AsyncExitStack
    ) -> None:

        async def sub_dep(var: uuid.UUID, greet: str, age: int = 15) -> dict:
            return {
                "var": var,
                "greet": greet,
                "age": age,
            }

        def call(sub: dict = Depends(sub_dep)) -> None:
            pass

        dependant = build_dependant(call)

        passed_vars = {
            "var": uuid.uuid4(),
            "greet": "Hello World",
        }
        dft_vars = {"age": 15}

        resolved = await resolve_dependencies(
            dependant,
            variables=passed_vars,
            builtins=mocked_builtins,
            exit_stack=exit_stack,
        )

        assert_that(resolved).is_not_none().is_type_of(ResolvedDependant)
        assert_that(resolved.kwargs).is_not_none().contains("sub")
        assert_that(resolved.kwargs["sub"]).contains_entry(**passed_vars, **dft_vars)

    @pytest.mark.asyncio
    async def test_with_async_context_manager(
        self, mocked_builtins: Builtins, exit_stack: AsyncExitStack
    ) -> None:

        async def sub_dep(
            var: uuid.UUID, greet: str, age: int = 15
        ) -> AsyncGenerator[dict[str, uuid.UUID | str | int], Any]:
            yield {"var": var, "greet": greet, "age": age}

        async def call(sub: dict = Depends(sub_dep)) -> None:
            pass

        passed_vars = {
            "var": uuid.uuid4(),
            "greet": "Hello World",
        }
        dft_vars = {"age": 15}
        dependant = build_dependant(call)

        resolved = await resolve_dependencies(
            dependant,
            variables=passed_vars,
            builtins=mocked_builtins,
            exit_stack=exit_stack,
        )

        assert_that(resolved).is_not_none().is_type_of(ResolvedDependant)
        assert_that(resolved.kwargs).is_not_none().contains("sub")
        assert_that(resolved.kwargs["sub"]).contains_entry(**passed_vars, **dft_vars)

    @pytest.mark.asyncio
    async def test_with_context_manager_decorated(
        self, mocked_builtins: Builtins, exit_stack: AsyncExitStack
    ) -> None:

        def sub_dep(
            var: uuid.UUID, greet: str, age: int = 15
        ) -> AsyncGenerator[dict[str, uuid.UUID | str | int], Any]:
            yield {"var": var, "greet": greet, "age": age}

        async def call(sub: dict = Depends(sub_dep)) -> None:
            pass

        passed_vars = {
            "var": uuid.uuid4(),
            "greet": "Hello World",
        }
        dft_vars = {"age": 15}
        dependant = build_dependant(call)

        resolved = await resolve_dependencies(
            dependant,
            variables=passed_vars,
            builtins=mocked_builtins,
            exit_stack=exit_stack,
        )

        assert_that(resolved).is_not_none().is_type_of(ResolvedDependant)
        assert_that(resolved.kwargs).is_not_none().contains("sub")
        assert_that(resolved.kwargs["sub"]).contains_entry(**passed_vars, **dft_vars)

    @pytest.mark.asyncio
    async def test_with_cached_deps(
        self, mocked_builtins: Builtins, exit_stack: AsyncExitStack
    ) -> None:

        call_count = 0

        async def sub_dep(var: uuid.UUID, greet: str, age: int = 15):
            nonlocal call_count
            call_count += 1
            return {"var": var, "greet": greet, "age": age}

        def other_dep(sub: dict = Depends(sub_dep)):
            return sub

        async def call(
            sub1: dict = Depends(sub_dep),
            sub2: dict = Depends(sub_dep),
            sub3: dict = Depends(other_dep),
        ) -> None:
            pass

        passed_vars = {
            "var": uuid.uuid4(),
            "greet": "Hello World",
        }
        dft_vars = {"age": 15}
        dependant = build_dependant(call)

        resolved = await resolve_dependencies(
            dependant,
            variables=passed_vars,
            builtins=mocked_builtins,
            exit_stack=exit_stack,
            dependency_cache={},
        )

        assert_that(resolved).is_not_none().is_type_of(ResolvedDependant)
        assert_that(resolved.kwargs).is_not_none().contains("sub1", "sub2", "sub3")
        assert_that(resolved.kwargs["sub1"]).contains_entry(**passed_vars, **dft_vars)
        assert_that(resolved.kwargs["sub2"]).contains_entry(**passed_vars, **dft_vars)
        assert_that(resolved.kwargs["sub3"]).contains_entry(**passed_vars, **dft_vars)
        assert_that(call_count).is_equal_to(1)

    def test_some(self, mocked_builtins):
        assert_that(mocked_builtins).is_not_none()
        assert_that(mocked_builtins).contains("context")
