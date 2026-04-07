from unittest.mock import MagicMock, PropertyMock, call, patch

import magic
import pytest
from pydantic import FilePath

from yio_minions.models.encoder import as_base64, camunda_encode_file, determine_mime


@patch("yio_minions.models.encoder.as_base64")
@patch("yio_minions.models.encoder.determine_mime")
def test_camunda_encode_file(mocked_determine_mime, mocked_as_base64):

    # Prepare
    mocked_file = MagicMock(FilePath)
    mocked_file_name = PropertyMock(return_value="test.pdf")
    type(mocked_file).name = mocked_file_name

    mocked_as_base64.return_value = "SGFsbG8K"  # Hallo
    mocked_determine_mime.return_value = "application/pdf"

    encoded = camunda_encode_file(mocked_file)

    # Assert
    mocked_as_base64.assert_called_once_with(mocked_file)
    mocked_determine_mime.assert_called_once_with(mocked_file)
    mocked_file_name.assert_called_once()
    assert encoded == {
        "value": "SGFsbG8K",
        "type": "File",
        "valueInfo": {
            "filename": "test.pdf",
            "mimetype": "application/pdf",
            "encoding": "utf-8",
        },
    }


mocked_file = MagicMock(FilePath)


@pytest.mark.parametrize(
    "ff_side_effect, gt_side_effect, ff_calls, gt_calls, expected_result",
    [
        pytest.param(
            ["application/pdf", NotImplementedError],
            ["application/json", NotImplementedError],
            [call(mocked_file, mime=True)],
            [],
            "application/pdf",
            id="from_file found",
        ),
        pytest.param(
            [magic.MagicException("some message"), NotImplementedError],
            [("application/json", None), NotImplementedError],
            [call(mocked_file, mime=True)],
            [call(mocked_file)],
            "application/json",
            id="from_file not found",
        ),
    ],
)
@patch("yio_minions.models.encoder.mimetypes.guess_type")
@patch("yio_minions.models.encoder.magic.from_file")
def test_determine_mime(
    mocked_from_file,
    mocked_guess_type,
    ff_side_effect,
    gt_side_effect,
    ff_calls,
    gt_calls,
    expected_result,
):

    # Prepare
    mocked_from_file.side_effect = ff_side_effect
    mocked_guess_type.side_effect = gt_side_effect

    # Execute
    mime_type = determine_mime(mocked_file)

    # Assert
    mocked_from_file.assert_has_calls(ff_calls)
    mocked_guess_type.assert_has_calls(gt_calls)
    assert mime_type == expected_result


@patch("yio_minions.models.encoder.base64.b64encode")
def test_as_base64(mocked_b64encode):

    # Prepare
    bytes_to_translate = "Hallo".encode("utf-8")  # Hallo
    mocked_b64encode.return_value = "SGFsbG8K".encode("utf-8")
    mocked_file = MagicMock(FilePath)
    mocked_file.read_bytes.return_value = bytes_to_translate

    # Execute
    base64 = as_base64(mocked_file)

    # Assert
    mocked_b64encode.assert_called_once_with(bytes_to_translate)
    mocked_file.read_bytes.assert_called_once()
    assert base64 == "SGFsbG8K"
