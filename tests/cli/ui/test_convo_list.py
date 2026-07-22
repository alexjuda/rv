from datetime import datetime

from pytest import CaptureFixture, fixture

from rv.cli.ui.convo import TextListConvoUI
from rv.domain.models.convo import ListEntry, PRCommentSummary, ThreadSummary


@fixture
def ui():
    return TextListConvoUI()


SAMPLE_TS = datetime.fromisoformat("2026-06-27T19:51:12+02:00")


class TestTextListConvoUI:
    class TestShowList:
        @staticmethod
        def test_entry_no_thread_replies(ui: TextListConvoUI, capsys: CaptureFixture):
            entries = [
                ListEntry(
                    id="1",
                    type="thread",
                    location="src/main.py:10",
                    author="alice",
                    state="unresolved",
                    body_excerpt="Fix this bug",
                    thread_summary=None,
                    summary=ThreadSummary(
                        n_replies=0, reply_authors=[], is_resolved=False
                    ),
                    created_at=SAMPLE_TS,
                ),
            ]
            ui.show_list(entries)
            out = capsys.readouterr().out
            assert "1" in out
            assert "src/main.py:10" in out
            assert "alice" in out
            assert "Fix this bug" in out

        @staticmethod
        def test_entry_with_thread_summary(ui: TextListConvoUI, capsys: CaptureFixture):
            entries = [
                ListEntry(
                    id="1",
                    type="thread",
                    location="src/lib.py:42",
                    author="bob",
                    state="resolved",
                    body_excerpt="Done",
                    thread_summary=ThreadSummary(
                        n_replies=3, reply_authors=["carol"], is_resolved=True
                    ),
                    summary=ThreadSummary(
                        n_replies=3, reply_authors=["carol"], is_resolved=True
                    ),
                    created_at=SAMPLE_TS,
                ),
            ]
            ui.show_list(entries)
            out = capsys.readouterr().out
            assert "resolved" in out
            assert "3" in out

        @staticmethod
        def test_pr_comment_entry(ui: TextListConvoUI, capsys: CaptureFixture):
            entries = [
                ListEntry(
                    id="3",
                    type="pr_comment",
                    location=None,
                    author="carol",
                    state=None,
                    body_excerpt="General comment",
                    thread_summary=None,
                    summary=PRCommentSummary(),
                    created_at=SAMPLE_TS,
                ),
            ]
            ui.show_list(entries)
            out = capsys.readouterr().out
            assert "carol" in out

    class TestFormatSummary:
        @staticmethod
        def test_pr_comment(ui: TextListConvoUI):
            assert ui.format_summary(PRCommentSummary()) == "PR comment"

        @staticmethod
        def test_thread_with_replies(ui: TextListConvoUI):
            assert (
                ui.format_summary(
                    ThreadSummary(
                        n_replies=5, reply_authors=["alice", "bob"], is_resolved=False
                    )
                )
                == "+5 replies from @alice, @bob"
            )

        @staticmethod
        def test_thread_without_replies(ui: TextListConvoUI):
            assert (
                ui.format_summary(
                    ThreadSummary(n_replies=0, reply_authors=[], is_resolved=False)
                )
                == ""
            )

        @staticmethod
        def test_thread_resolved(ui: TextListConvoUI):
            assert (
                ui.format_summary(
                    ThreadSummary(
                        n_replies=1, reply_authors=["alice"], is_resolved=True
                    )
                )
                == "(resolved) +1 reply from @alice"
            )
