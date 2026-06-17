from datetime import datetime, timedelta

from pytest import CaptureFixture, fixture

from rv.cli.ui.pr_list import TextPRListUI
from rv.domain.models.actions import PRListEntry


SAMPLE_DT = datetime.fromisoformat("2026-06-27T19:51:12+02:00")


class FakePREntries:
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
            title="fix memory leak",
            author="carol",
            n_unresolved_threads=1,
            effective_review_state="commented",
            n_pending_thread_comments=0,
            last_synced_at=SAMPLE_DT - timedelta(days=2),
            is_stale=True,
            pr_state="open",
        )

    @staticmethod
    def update_template() -> PRListEntry:
        return PRListEntry(
            pr_number=43,
            title="update template",
            author="dylan",
            n_unresolved_threads=0,
            effective_review_state=None,
            n_pending_thread_comments=0,
            last_synced_at=SAMPLE_DT,
            is_stale=False,
            pr_state="open",
        )

    @staticmethod
    def update_dependencies() -> PRListEntry:
        return PRListEntry(
            pr_number=41,
            title="update dependencies",
            author="alice",
            n_unresolved_threads=0,
            effective_review_state="approved",
            n_pending_thread_comments=0,
            last_synced_at=SAMPLE_DT,
            is_stale=False,
            pr_state="open",
        )

    @staticmethod
    def add_ci_pipeline() -> PRListEntry:
        return PRListEntry(
            pr_number=35,
            title="add ci pipeline",
            author="bob",
            n_unresolved_threads=0,
            effective_review_state="approved",
            n_pending_thread_comments=0,
            last_synced_at=SAMPLE_DT,
            is_stale=False,
            pr_state="merged",
        )


class TestTextPRListUI:
    @fixture
    @staticmethod
    def ui():
        return TextPRListUI()

    class TestShowAll:
        @staticmethod
        def test_some_data(ui: TextPRListUI, capsys: CaptureFixture):
            entries = [
                FakePREntries.add_user_authentication(),
                FakePREntries.refactor_db_layer(),
            ]
            ui.show_all(entries)

            out: str = capsys.readouterr().out
            lines = out.splitlines()
            assert len(lines) >= len(entries)

    class TestSummary:
        @staticmethod
        def test_unresolved_changes_requested(ui: TextPRListUI):
            entry = FakePREntries.add_user_authentication()

            summary = ui.summary(entry)

            assert "3 unresolved" in summary
            assert "changes requested" in summary

        @staticmethod
        def test_pending_replies(ui: TextPRListUI):
            entry = FakePREntries.refactor_db_layer()

            summary = ui.summary(entry)

            assert str(summary) == "2 pending replies"

        @staticmethod
        def test_commented_only(ui: TextPRListUI):
            entry = FakePREntries.fix_memory_leak()

            summary = ui.summary(entry)

            assert str(summary) == "1 unresolved"

        @staticmethod
        def test_no_traction(ui: TextPRListUI):
            entry = FakePREntries.update_template()

            summary = ui.summary(entry)

            assert str(summary) == "no traction yet"

    class TestSyncStatus:
        @staticmethod
        def test_unresolved_changes_requested(ui: TextPRListUI):
            entry = FakePREntries.add_user_authentication()
            now = entry.last_synced_at + timedelta(hours=2, seconds=2)

            assert str(ui.sync_status(entry, now)) == "2 hours ago"

        @staticmethod
        def test_pending_replies(ui: TextPRListUI):
            entry = FakePREntries.refactor_db_layer()

            assert str(ui.sync_status(entry)) == "not pushed"

        @staticmethod
        def test_stale(ui: TextPRListUI):
            entry = FakePREntries.fix_memory_leak()
            now = entry.last_synced_at + timedelta(days=2)

            assert str(ui.sync_status(entry, now)) == "stale (2 days)"

        @staticmethod
        def test_a_moment_ago(ui: TextPRListUI):
            entry = FakePREntries.update_template()
            now = entry.last_synced_at + timedelta(milliseconds=800)

            assert str(ui.sync_status(entry, now)) == "now"
