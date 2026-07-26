from .models import Signal, Message


class ContextError(Exception):
    """
    An error occurred while dealing with context
    """

    pass


class UnexpectedEventReceived(ContextError):
    """
    Occurs when an unexpected event is received (this should not happen)
    """


class SignalFailureError(ContextError):
    """
    Raised when a signal cannot be emitted
    """

    signal: Signal

    def __init__(self, *args, signal: Signal):
        super().__init__(*args)
        self.signal = signal


class MessageCorrelateError(ContextError):
    message: Message

    def __init__(self, *args, message: Message):
        super().__init__(*args)
        self.message = message


class VariableFetchError(ContextError):
    variable_name: str
    file_path: str

    def __init__(self, *args, variable_name: str, file_path: str):
        super().__init__(*args)
        self.variable_name = variable_name
        self.file_path = file_path
