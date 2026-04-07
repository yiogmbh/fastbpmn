from typing import Protocol, runtime_checkable


@runtime_checkable
class SquirrelBaseSettings(Protocol):
    """
    Override this class with custom settings if required.
    """

    # Ensure to override this method returning the flavour to represent
    @property
    def flavour(self) -> str:
        """
        Should be overridden by subclasses to expose which flavour is used.
        """
        ...

    def as_kwargs(self) -> dict:
        """
        Should be overridden by subclasses to render the given settings such that
        all values are accessible by keys understood by the flavour.
        """
        ...
