from datetime import datetime

from pytest import CaptureFixture, fixture

from rv.cli.ui.convo import TextListConvoUI
from rv.domain.models.convo import ListEntry, ThreadSummary


@fixture
def ui():
    return TextListConvoUI()


SAMPLE_TS = datetime.fromisoformat("2026-06-27T19:51:12+02:00")


class TestTextListConvoUI:
    class TestShowList:
        @staticmethod
        def test_entry_no_thread_summary(ui: TextListConvoUI, capsys: CaptureFixture):
            entries = [
                ListEntry(
                    id="1",
                    type="thread",
                    location="src/main.py:10",
                    author="alice",
                    state="unresolved",
                    body_excerpt="Fix this bug",
                    thread_summary=None,
                    summary=None,
                    created_at=SAMPLE_TS,
                ),
            ]
            ui.show_list(entries)
            out = capsys.readouterr().out
            assert "1" in out
            assert "src/main.py:10" in out
            assert "alice" in out
            assert "unresolved" in out
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
                    thread_summary=ThreadSummary(n_replies=3, reply_authors=["carol"]),
                    summary=ThreadSummary(n_replies=3, reply_authors=["carol"]),
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
                    summary=None,
                    created_at=SAMPLE_TS,
                ),
            ]
            ui.show_list(entries)
            out = capsys.readouterr().out
            assert "carol" in out

    class TestFormatSummary:
        @staticmethod
        def test_none(ui: TextListConvoUI):
            assert ui.format_summary(None) == ""

        @staticmethod
        def test_format_thread_with_replies(ui: TextListConvoUI):
            assert (
                ui.format_summary(
                    ThreadSummary(n_replies=5, reply_authors=["alice", "bob"])
                )
                == "+5 replies from @alice, @bob"
            )
