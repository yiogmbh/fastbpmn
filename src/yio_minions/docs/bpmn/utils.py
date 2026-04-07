from base64 import b64encode
from urllib import error, request
from uuid import uuid4


def request_diagram(url: str) -> str:

    httprequest = request.Request(url, method="GET")

    try:
        with request.urlopen(httprequest) as response:
            return response.read().decode(response.headers.get_content_charset("utf-8"))
    except error.HTTPError as exc:
        return (
            f"Diagramm kann nicht geladen werden (url<{exc.url}, error<{exc.reason}>)"
        )


def render_reload(
    source: str,
    language,
    css_class,
    options,
    md,
    classes=None,
    id_value="",
    attrs=None,
    **kwargs,
) -> str:
    # pylint: disable=unused-argument, invalid-name, line-too-long, too-many-arguments

    help_text = """<span style="color: darkred;">Aktiviere JavaScript und/oder führe einen Reload durch um das Diagramm anzuzeigen!</span>"""

    id_value = id_value if id_value and len(id_value) > 0 else f"bpmn-{str(uuid4())}"

    if "src" in attrs:
        diagram_source = request_diagram(attrs["src"])
    else:
        diagram_source = source

    diagram_source_b64 = b64encode(diagram_source.encode(encoding="utf-8")).decode(
        encoding="utf-8"
    )

    return f'<div id="{id_value}" class="{css_class}" data-bpmn="{diagram_source_b64}">{help_text}</div>'
