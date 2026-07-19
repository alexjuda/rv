from typing import Protocol

from ..models.actions import CollectionStat, StatusSummary, ThreadStat
from ..ports import Store


class StatusUI(Protocol):
    def show_summary(self, summary: StatusSummary): ...


class Status:
    def __init__(self, store: Store, ui: StatusUI):
        self._store = store
        self._ui = ui

    def exec(self) -> None:
        n_prs = self._store.count_prs()
        unresolved = self._store.count_threads_prs(resolved=False)

        # Other stats will be populated as we implement storage for the remaining commands.
        summary = StatusSummary(
            stored_n_prs=n_prs,
            pending_comments_stat=CollectionStat.empty(),
            pending_threads_stat=ThreadStat.empty(),
            pending_n_prs=0,
            unresolved_n_threads=unresolved[1],
            unresolved_n_prs=unresolved[0],
            stale_n_prs=0,
            unreviewed_n_prs=0,
            reviewed_n_prs=0,
        )
        self._ui.show_summary(summary)
