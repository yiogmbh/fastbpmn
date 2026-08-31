from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path
from typing import Any


DOCS_ROOT = Path(__file__).parent / "docs"


def _asset_path(path: str) -> tuple[Path, str]:
    relative_path = Path(path)
    if relative_path.is_absolute() or relative_path.suffix.lower() != ".bpmn":
        raise ValueError(f"BPMN path must be a relative .bpmn file: {path}")

    resolved_path = (DOCS_ROOT / relative_path).resolve()
    if not resolved_path.is_relative_to(DOCS_ROOT.resolve()):
        raise ValueError(f"BPMN path is outside the documentation tree: {path}")
    if not resolved_path.is_file():
        raise FileNotFoundError(f"BPMN file does not exist: {path}")

    return resolved_path, relative_path.as_posix()


def bpmn(
    path: str,
    page_url: str = "",
    title: str | None = None,
    min_height: str | None = None,
    config: str | None = None,
) -> str:
    """Return a read-only BPMN viewer container for a documentation page."""
    source_path, asset_path = _asset_path(path)
    source_url = "data:application/xml;base64," + base64.b64encode(
        source_path.read_bytes()
    ).decode("ascii")
    identity = hashlib.sha256(f"{page_url}:{asset_path}".encode()).hexdigest()[:12]
    label = title or Path(path).stem.replace("-", " ").replace("_", " ").title()

    escaped_id = html.escape(f"bpmn-viewer-{identity}", quote=True)
    _escaped_url = html.escape(source_url, quote=True)
    escaped_path = html.escape(asset_path, quote=True)
    escaped_label = html.escape(label, quote=True)

    viewer_config = json.dumps(json.loads(config or "{}"))

    html_fragment = f"""
<div
    class="bpmn-viewer" id="{escaped_id}"
    style="min-height: {min_height or "0px"}"
    data-bpmn-src="{escaped_path}"
    data-bpmn-title="{escaped_label}"
    role="img" aria-label="{escaped_label}"
>
<script type="application/json" charset="utf-8" class="bpmn-viewer-config">
{viewer_config}
</script>
<div class="bpmn-viewer__canvas"></div>
    <div class="bpmn-viewer__selection" aria-live="polite">
        Select an element to inspect it.
    </div>
</div>
"""
    return html_fragment


def define_env(env: Any) -> None:
    env.macro(bpmn)
