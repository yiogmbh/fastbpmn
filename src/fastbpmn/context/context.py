from asyncio import shield
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

from .exceptions import SignalFailureError, MessageCorrelateError
from .models import Signal, Message, MessageResult, MessageFailure

from .io import Delete
from .utils import create_temp_dir, create_temp_file, delete_all
from .types import MessageCorrelator, SignalEmitter

if TYPE_CHECKING:
    from fastbpmn.models.base import FileInfo


FileDownloader = Callable[[str], Awaitable[bytes]]


class Context:
    """
    A context is created for each task execution to provide additional useful features.

    Features:
        - create temporary files/directories to be used within your external task routine. If you want so
          this files/directories will be removed automatically as soon as the task is completed (either error or not).
    """

    __slots__ = [
        "temp_paths",
        "_file_downloader",
        "_message_correlator",
        "_signal_emitter",
    ]

    def __init__(
        self,
        file_downloader: FileDownloader,
        message_correlator: MessageCorrelator,
        signal_emitter: SignalEmitter,
    ):
        self.temp_paths = []
        self._file_downloader = file_downloader
        self._message_correlator = message_correlator
        self._signal_emitter = signal_emitter

    async def __aenter__(self):
        """
        Perform required actions to be performed whenever a task execution gets started.
        """

        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        """
        Perform cleanup actions to be done whenever the task is completed
        :param exc_t:
        :param exc_v:
        :param exc_tb:
        :return:
        """
        error = (exc_t or exc_v or exc_tb) is not None

        # try to come around the non deleted temp files issue, by shielding the coroutine
        delete_t = shield(delete_all(temp_paths=self.temp_paths, error=error))
        await delete_t

    def temp_dir(self, flags: Delete = Delete.ALWAYS) -> Path:
        """
        Obtain a temporary directory within the context of an external task.
        Depending on the given flags argument the Directory is removed automatically.
        :param flags: determines under which conditions the directory should be removed (default: Delete.ALWAYS)
        :return: the temp directory created as Path
        """
        temp = create_temp_dir(flags=flags)
        self.temp_paths.append(temp)
        return temp.path

    def temp_file(self, flags: Delete = Delete.ALWAYS, *, suffix: str = None) -> Path:
        """
        Obtain a temporary file within the context of an external task.
        Depending on the given flags argument the File is removed automatically.
        :param flags: determines under which conditions the file should be removed (default: Delete.ALWAYS)
        :param suffix: an optional suffix (maybe required by other tools like Latex, ...)
        :return: the temp directory created as Path
        """
        temp = create_temp_file(flags=flags, suffix=suffix)
        self.temp_paths.append(temp)
        return temp.path

    def temp_file_in_dir(self, filename, flags: Delete = Delete.ALWAYS) -> Path:
        temp = self.temp_dir(flags)

        return temp / filename

    async def download_file(
        self, file_info: "FileInfo", flags: Delete = Delete.ALWAYS
    ) -> Path:
        """
        Download a file from the Camunda Engine and return it as Path.
        :param file_info: the file info as provided by the Camunda Engine
        :return: the downloaded file as Path
        """
        target_path = (
            self.temp_file_in_dir(file_info.filename, flags)
            if file_info.filename
            else self.temp_file(flags)
        )

        contents = await self._file_downloader(file_info.variable)
        target_path.write_bytes(contents)

        return target_path

    async def emit_signal(self, signal: Signal) -> None:
        """
        Emits the given signal to the process engine
        :param signal: the signal to be emitted
        :raises SignalFailureError: if the signal could not be emitted
        """
        result = await self._signal_emitter(signal)

        if not result.success:
            raise SignalFailureError(
                result.error_message or "Unknown Error", signal=signal
            )

    async def correlate_message(self, message: Message) -> MessageResult:
        """
        Correlates the given message to the process engine
        :param message: the message to be correlated
        :return: MessageResult in case of success, otherwise an Exception
        :raises MessageCorrelateError: if the message cannot be correlated
        """
        result = await self._message_correlator(message)

        if isinstance(result, MessageFailure):
            raise MessageCorrelateError(
                result.error_message or "Unknown Error", message=message
            )

        return result
