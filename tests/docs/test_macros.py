from pathlib import Path

import pytest

from docs.macros import bpmn


def test_bpmn_returns_embedded_viewer_container() -> None:
    rendered = bpmn(
        "assets/bpmn/greeting.bpmn",
        page_url="features/builtins/",
        title="Greeting process",
    )

    assert 'class="bpmn-viewer"' in rendered
    assert 'data-bpmn-src="assets/bpmn/greeting.bpmn"' in rendered
    assert 'data-bpmn-title="Greeting process"' in rendered


def test_bpmn_rejects_paths_outside_docs() -> None:
    with pytest.raises(ValueError, match="outside the documentation tree"):
        bpmn("../outside.bpmn")


def test_bpmn_rejects_missing_files() -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        bpmn("assets/bpmn/missing.bpmn")


def test_bpmn_rejects_non_bpmn_files() -> None:
    with pytest.raises(ValueError, match="relative .bpmn file"):
        bpmn(Path("assets/bpmn/greeting.xml").as_posix())
