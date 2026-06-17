from datetime import datetime, timedelta

from rv.cli.ui.pr_list import TextPRListUI
from rv.domain.models.actions import PRListEntry

SAMPLE_DT = datetime.fromisoformat("2026-06-27T19:51:12+02:00")


class FakePREntries:
    # Factories matching the examples in rv-pr-list.md
    # rv pr list: Action needed

    @staticmethod
    def add_user_authentication() -> PRListEntry:
        return PRListEntry(
            pr_number=42,
            title="add user authentication",
            author="alice",
            n_unresolved_threads=3,
            effective_review_state="changes_requested",
            n_pending_thread_comments=0,
            last_synced_at=SAMPLE_DT,
            is_stale=False,
            pr_state="open",
        )

    @staticmethod
    def refactor_db_layer() -> PRListEntry:
        return PRListEntry(
            pr_number=40,
            title="refactor db layer",
            author="bob",
            n_unresolved_threads=2,
            effective_review_state="commented",
            n_pending_thread_comments=2,
            last_synced_at=SAMPLE_DT,
            is_stale=True,
            pr_state="open",
        )

    @staticmethod
    def fix_memory_leak() -> PRListEntry:
        return PRListEntry(
            pr_number=38,
            title="fix(AB-1234): fix memory leak in controller manager when tools are used with utils",
            author="carol",
            n_unresolved_threads=1,
            effective_review_state="commented",
            n_pending_thread_comments=0,
            last_synced_at=SAMPLE_DT - timedelta(days=2),
            is_stale=True,
            pr_state="open",
        )


ui = TextPRListUI()
ui.show_all(
    [
        FakePREntries.add_user_authentication(),
        FakePREntries.refactor_db_layer(),
        FakePREntries.fix_memory_leak(),
    ]
)
