class Error(Exception):
    """Base Error Class.

    Attributes:
        message -- explanation of the error
        hint -- optional explanation

    """

    def __init__(self, message: str = None, hint: str = None):
        self.message = message
        self.hint = hint
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} -> {self.hint}"


class ProcessNotFound(Error):
    """
    Exception raised if process id does not exists
    """


class ProcessInstanceError(Error):
    """Exception raised for common errors whilst using process instance.

    Attributes:
        message -- explanation of the error
        hint -- optional explanation
    """


class ProcessError(Error):
    """
    Exception raised for common errors whilst using process engine.
    """


class TaskFailure(Error):
    """
    Ends external Task with a failure.

    Attributes:
        code -- a failure code
        message -- explanation of the failure
        retries -- number of retries left, default = None
        timeout -- time until next retry in ms
        hint -- Further details on the Failure
    """

    # pylint: disable=too-many-arguments

    def __init__(
        self,
        code: str = "FAILURE",
        message: str = None,
        retries: int = None,
        timeout: int = None,
        hint: str = None,
    ):

        self.code = code
        self.message = message
        self.retries = retries
        self.timeout = timeout
        self.hint = hint

        # ToDo: what todo with hint - it'S

        super().__init__(self.message, self.hint)

    def __str__(self):
        return f"{self.code}: {self.message}"


class TaskError(Error):
    """
    Ends external Task with an error.

    Attributes:
        code -- an error code
        message -- explanation of the error
    """

    def __init__(self, code: str = "BPMN_ERROR", message: str = None, hint: str = None):

        self.code = code
        self.message = message
        self.hint = hint
        super().__init__(self.message, self.hint)

    def __str__(self):
        return f"{self.code}: {self.message}"


class RetryableError(Error):
    pass


class OptimisticLockError(RetryableError):
    """
    Occurs in camunda sometimes
    """

    pass


class DeadlockSituationOccurredError(RetryableError):
    pass
