from aetpiref.typing import ExternalTaskScope
from culsans import Queue


class UniqueQueue(Queue[ExternalTaskScope]):
    def _init(self, maxsize):
        self.data = dict()

    def _qsize(self):
        return len(self.data)

    def _put(self, item: ExternalTaskScope):

        task_scope = item["task"]

        if task_scope["id"] not in self.data:
            self.data[task_scope["id"]] = item

    def _get(self) -> ExternalTaskScope:
        key = next(iter(self.data), None)
        return self.data.pop(key)

        return self.data.pop()

    def _peekable(self):
        return False

    _peek = None

    def _clearable(self):
        return True

    def _clear(self):
        self.data.clear()
