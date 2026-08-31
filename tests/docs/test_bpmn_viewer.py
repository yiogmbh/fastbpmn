from pathlib import Path


def test_bpmn_viewer_children_fill_the_available_space() -> None:
    stylesheet = (
        Path(__file__).parents[2] / "docs" / "docs" / "stylesheets" / "bpmn-viewer.css"
    ).read_text()

    canvas_rules = stylesheet.split(".bpmn-viewer__canvas {", 1)[1].split("}", 1)[0]
    bjs_rules = stylesheet.split(".bpmn-viewer__canvas > .bjs-container {", 1)[1].split(
        "}", 1
    )[0]

    assert "width: 100%;" in canvas_rules
    assert "height: 100%;" in canvas_rules
    assert "min-width: 0;" in canvas_rules
    assert "min-height: 0;" in canvas_rules
    assert "width: 100%;" in bjs_rules
    assert "height: 100%;" in bjs_rules
    assert "min-width: 0;" in bjs_rules
    assert "min-height: 0;" in bjs_rules
    assert ".bpmn-viewer__canvas .djs-container" in stylesheet
    assert ".bpmn-viewer__canvas svg" in stylesheet
    assert "display: block;" in stylesheet
    assert "max-width: none;" in stylesheet
