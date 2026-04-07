from functools import cached_property
from unittest.mock import MagicMock

import pytest
from pydantic import (
    AliasChoices,
    Field,
    computed_field,
    model_validator,
)

from yio_minions.models import BaseInputModel, FileInfo
from yio_minions.models.base import get_file_info_indirect


def test_file_info():
    class InputModel(BaseInputModel):
        file: FileInfo

    mocked_file = MagicMock(FileInfo)

    variables = {"file": mocked_file}

    model = InputModel(**variables)

    assert model.file == mocked_file


def test_file_info_with_alias():

    class InputModel(BaseInputModel):
        file: FileInfo = Field(
            ..., validation_alias=AliasChoices("the_file", "other_file")
        )

    mocked_file = MagicMock(FileInfo)

    variables1 = {"the_file": mocked_file}
    variables2 = {"other_file": mocked_file}
    variables3 = {"file": mocked_file}

    model1 = InputModel(**variables1)
    model2 = InputModel(**variables2)

    assert model1.file == mocked_file
    assert model2.file == mocked_file

    with pytest.raises(ValueError) as error:
        InputModel(**variables3)
    assert "Field required" in str(error.value)


@pytest.mark.parametrize(
    "file_var, file_info_var, file_info, required, error",
    [
        pytest.param(
            "somewhere",
            "somewhere",
            "Other type",
            True,
            "Var: somewhere is not a FileInfo (indirect lookup)",
            id="Not a FileInfo",
        ),
        pytest.param(
            "somewhere",
            "somewhere",
            "Other type",
            False,
            "Var: somewhere is not a FileInfo (indirect lookup)",
            id="Not a FileInfo (not required)",
        ),
        pytest.param(
            "anywhere",
            "somewhere",
            MagicMock(FileInfo),
            True,
            "Var: anywhere is empty/None/not existing (indirect lookup)",
            id="Missing FileInfo",
        ),
        pytest.param(
            "somewhere",
            "somewhere",
            None,
            True,
            "Var: somewhere is empty/None/not existing (indirect lookup)",
            id="Missing FileInfo (none)",
        ),
        pytest.param(
            "somewhere",
            "somewhere",
            None,
            False,
            None,
            id="Missing FileInfo (not required)",
        ),
        pytest.param(
            "somewhere", "somewhere", MagicMock(FileInfo), True, None, id="Valid"
        ),
        pytest.param(
            "somewhere",
            "somewhere",
            MagicMock(FileInfo),
            False,
            None,
            id="Valid (not required)",
        ),
    ],
)
def test_indirect_file_info(file_var, file_info_var, file_info, required, error):

    if required:

        class InputModel(BaseInputModel):
            file_var: str

            @computed_field
            @cached_property
            def file(self) -> FileInfo:
                return get_file_info_indirect(self, self.file_var, required=True)

            @model_validator(mode="after")
            def check_file(self):
                """
                Checks if the file_info is present at the given key
                """
                # this is a way to compute the value of the computed_field on initialization
                # to trigger validation immediately
                _ = self.file

                return self
    else:

        class InputModel(BaseInputModel):
            file_var: str

            @computed_field
            @cached_property
            def file(self) -> FileInfo | None:
                return get_file_info_indirect(self, self.file_var, required=False)

            @model_validator(mode="after")
            def check_file(self):
                """
                Checks if the file_info is present at the given key
                """
                # this is a way to compute the value of the computed_field on initialization
                # to trigger validation immediately
                _ = self.file

                return self

    variables = {"file_var": file_var, file_info_var: file_info}

    if error:
        with pytest.raises(ValueError) as e:
            model = InputModel(**variables)

        assert error in str(e.value)

    else:
        model = InputModel(**variables)

        assert model.file == file_info
        assert model.file_var == file_info_var


def test_multiple_indirect_files():
    """
    Test some cases with mixed and multiple indirect file infos
    """

    class InputModel(BaseInputModel):
        pdf_file_var: str
        png_file_var: str

        @computed_field
        @cached_property
        def pdf_file(self) -> FileInfo:
            return get_file_info_indirect(self, self.pdf_file_var, required=True)

        @computed_field
        @cached_property
        def png_file(self) -> FileInfo | None:
            return get_file_info_indirect(self, self.png_file_var, required=False)

        @model_validator(mode="after")
        def check_file(self):
            """
            Checks if the file_info is present at the given key
            """
            # this is a way to compute the value of the computed_field on initialization
            # to trigger validation immediately
            _ = self.png_file
            return self

        @model_validator(mode="after")
        def check_pdf_file(self):
            """
            Checks if the file_info is present at the given key
            """
            # this is a way to compute the value of the computed_field on initialization
            # to trigger validation immediately
            _ = self.pdf_file

            return self

    case1 = {
        "pdf_file_var": "pdf_file_info",
        "png_file_var": "png_file_info",
        "pdf_file_info": MagicMock(FileInfo),
        "png_file_info": MagicMock(FileInfo),
    }
    case2 = {
        "pdf_file_var": "pdf_file_info",
        "png_file_var": "png_file_info",
        "pdf_file_info": MagicMock(FileInfo),
        "png_file_info": None,
    }
    model1 = InputModel(**case1)
    model2 = InputModel(**case2)

    assert model1.pdf_file == case1["pdf_file_info"]
    assert model1.pdf_file_var == case1["pdf_file_var"]
    assert model1.png_file == case1["png_file_info"]
    assert model1.png_file_var == case1["png_file_var"]

    assert model2.pdf_file == case2["pdf_file_info"]
    assert model2.pdf_file_var == case2["pdf_file_var"]
    assert model2.png_file == case2["png_file_info"]
    assert model2.png_file_var == case2["png_file_var"]

    # Pass unexpected type to png_file_info
    with pytest.raises(ValueError) as error1:
        InputModel(
            **{
                "pdf_file_var": "pdf_file_info",
                "png_file_var": "png_file_info",
                "pdf_file_info": MagicMock(FileInfo),
                "png_file_info": "Other type",
            }
        )

    assert "Var: png_file_info is not a FileInfo (indirect lookup)" in str(error1.value)

    # Pass None to pdf_file_info (but is required)
    with pytest.raises(ValueError) as error2:
        InputModel(
            **{
                "pdf_file_var": "pdf_file_info",
                "png_file_var": "png_file_info",
                "pdf_file_info": None,
                "png_file_info": MagicMock(FileInfo),
            }
        )

    assert "Var: pdf_file_info is empty/None/not existing (indirect lookup)" in str(
        error2.value
    )

    # Pass unexpected type to pdf_file_info
    with pytest.raises(ValueError) as error3:
        InputModel(
            **{
                "pdf_file_var": "pdf_file_info",
                "png_file_var": "png_file_info",
                "pdf_file_info": "some other type",
                "png_file_info": MagicMock(FileInfo),
            }
        )
    assert "Var: pdf_file_info is not a FileInfo (indirect lookup)" in str(error3.value)


def test_indirect_file_info_list():
    """
    Just for sake of completeness an example with a list of indirect file infos
    """

    class InputModel(BaseInputModel):
        file_vars: list[str]

        @computed_field
        @cached_property
        def files(self) -> list[FileInfo]:
            return [
                get_file_info_indirect(self, x, required=True) for x in self.file_vars
            ]

        @model_validator(mode="after")
        def check_files(self):
            """
            Checks if the file_info is present at the given key
            """
            # this is a way to compute the value of the computed_field on initialization
            # to trigger validation immediately
            _ = self.files
            return self

    all_ok = {
        "file_vars": ["file1", "file2", "file3"],
        "file1": MagicMock(FileInfo),
        "file2": MagicMock(FileInfo),
        "file3": MagicMock(FileInfo),
    }
    model_ok = InputModel(**all_ok)

    assert model_ok.files == [all_ok["file1"], all_ok["file2"], all_ok["file3"]]
    assert model_ok.file_vars == all_ok["file_vars"]
    assert len(model_ok.files) == len(model_ok.file_vars)

    with pytest.raises(ValueError) as error1:
        InputModel(
            **{
                "file_vars": ["file1", "file2", "file3"],
                "file1": MagicMock(FileInfo),
                "file2": MagicMock(FileInfo),
                "file3": "Other type",
            }
        )
    assert "Var: file3 is not a FileInfo (indirect lookup)" in str(error1.value)
