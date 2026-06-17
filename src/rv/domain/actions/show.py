from typing import Protocol

from ..exceptions import IDNotFoundError
from ..models.github import Thread, ThreadComment
from ..ports import Store


class ShowUI(Protocol):
    def show_thread(self, thread: Thread) -> None:
        """
        Present a single thread to the user, with the comments.
        """

    def show_thread_comment(self, thread_comment: ThreadComment) -> None:
        """
        Present a single comment to the user.
        """


class Show:
    def __init__(self, store: Store, ui: ShowUI):
        self._store = store
        self._ui = ui

    async def exec(self, id: str) -> None:
        if thread := self._store.get_thread(id):
            self._ui.show_thread(thread)
            return
        elif thread_comment := self._store.get_thread_comment(id):
            self._ui.show_thread_comment(thread_comment)
            return
        else:
            raise IDNotFoundError()
