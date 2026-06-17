from typing import Protocol

from ..models.github import Thread, ThreadComment
from ..ports import Store


class CompleteIDsUI(Protocol):
    def format_thread(self, thread: Thread) -> tuple[str, str]: ...
    def format_thread_comment(
        self, thread_comment: ThreadComment
    ) -> tuple[str, str]: ...


class CompleteIDs:
    def __init__(self, store: Store, ui: CompleteIDsUI):
        self._store = store
        self._ui = ui

    def exec(self, id_prefix: str) -> list[tuple[str, str]]:
        threads = self._store.get_threads_matching(id_prefix)
        th_comms = self._store.get_thread_comments_matching(id_prefix)

        return [self._ui.format_thread(th) for th in threads] + [
            self._ui.format_thread_comment(comm) for comm in th_comms
        ]
