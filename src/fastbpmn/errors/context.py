import inspect
from typing import Any, TypedDict


class HandlerContext(TypedDict, total=False):
    function: str
    path: str
    file: str
    line: int


# Cache for endpoint context to avoid re-extracting on every request
_handler_context_cache: dict[int, HandlerContext] = {}


def _extract_endpoint_context(func: Any) -> HandlerContext:
    """Extract endpoint context with caching to avoid repeated file I/O."""
    func_id = id(func)

    if func_id in _handler_context_cache:
        return _handler_context_cache[func_id]

    try:
        ctx: HandlerContext = {}

        if (source_file := inspect.getsourcefile(func)) is not None:
            ctx["file"] = source_file
        if (line_number := inspect.getsourcelines(func)[1]) is not None:
            ctx["line"] = line_number
        if (func_name := getattr(func, "__name__", None)) is not None:
            ctx["function"] = func_name
    except Exception:
        ctx = HandlerContext()

    _handler_context_cache[func_id] = ctx
    return ctx
