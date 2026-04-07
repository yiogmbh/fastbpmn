def render(
    source: str,
    language,
    css_class,
    options,
    md,
    classes=None,
    id_value="",
    attrs=None,
    **kwargs,
):
    """
    This method receives input from superfences trying to render a bpmn diagram.

    :param source:
    :param language:
    :param css_class:
    :param options:
    :param md:
    :param classes:
    :param id_value:
    :param attrs:
    :param kwargs:
    :return:
    """
    # pylint: disable=invalid-name,too-many-arguments,import-outside-toplevel
    from .utils import render_reload

    return render_reload(
        source,
        language,
        css_class,
        options,
        md,
        classes=classes,
        id_value=id_value,
        attrs=attrs,
        **kwargs,
    )
