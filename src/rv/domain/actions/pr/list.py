from typing import Protocol

from ...models.actions import PRList, PRListCategorized, PRListEntry
from ...models.github import ReviewState
from ...models.storage import StoredPR
from ...ports import Store


class PRListUI(Protocol):
    def show_categorized(self, pr_list: PRListCategorized) -> None:
        """
        Show PRs grouped into sections.
        """

    def show_all(self, pr_list: PRList) -> None:
        """
        Show PRs in a single flat collection.
        """


class PRList:
    def __init__(self, store: Store, ui: PRListUI):
        self._store = store
        self._ui = ui

    def exec(self) -> None:
        stored = self._store.list_prs()
        entries = [_build_entry(s) for s in stored]
        self._ui.show_all(entries)


def _build_entry(stored: StoredPR) -> PRListEntry:
    threads = stored.pr.convo.threads
    reviews = stored.pr.convo.reviews

    n_unresolved = sum(1 for t in threads if not t.is_resolved)

    effective_review_state: ReviewState | None = None
    if reviews:
        states = {r.state for r in reviews}
        if "changes_requested" in states:
            effective_review_state = "changes_requested"
        elif "approved" in states:
            effective_review_state = "approved"
        else:
            effective_review_state = "commented"

    return PRListEntry(
        pr_number=stored.pr.pr.locator.number,
        title=stored.pr.pr.title,
        author=stored.pr.pr.author,
        n_unresolved_threads=n_unresolved,
        effective_review_state=effective_review_state,
        n_pending_thread_comments=0,
        last_synced_at=stored.meta.synced_at,
        is_stale=False,
        pr_state=stored.pr.pr.state,
    )
