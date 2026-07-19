from datetime import UTC, datetime
from io import StringIO

from rich.console import Console

from rv.cli.ui.convo_show import RichShowConvoUI
from rv.domain.actions.convo.show import CodeContext
from rv.domain.models.github import PRLocator, RepoLocator, Thread, ThreadComment


class TestRichShowConvoUI:
    @staticmethod
    def test_show_thread_renders_pr_header():
        console = Console(file=StringIO(), width=80, color_system=None)
        ui = RichShowConvoUI(console=console)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        thread = Thread(
            id="thr_1",
            is_resolved=False,
            path="src/main.py",
            line=42,
            commit_sha="abc123",
            comments=[
                ThreadComment(
                    id="c1",
                    body="Fix this",
                    author="alice",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
            ],
        )

        ui.show_thread(thread, pr_loc, context=None)

        out = console.file.getvalue()  # type: ignore
        assert "owner/repo#42" in out
        assert "src/main.py:42" in out
        assert "alice" in out

    @staticmethod
    def test_show_thread_with_code_context():
        console = Console(file=StringIO(), width=80, color_system=None)
        ui = RichShowConvoUI(console=console)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        thread = Thread(
            id="thr_1",
            is_resolved=False,
            path="src/main.py",
            line=7,
            commit_sha="abc123",
            comments=[
                ThreadComment(
                    id="c1",
                    body="Fix this",
                    author="alice",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
            ],
        )
        context = CodeContext(
            path="src/main.py",
            commit_sha="abc123",
            target_line=7,
            start_line=5,
            lines=["line5", "line6", "line7", "line8", "line9"],
        )

        ui.show_thread(thread, pr_loc, context)

        out = console.file.getvalue()  # type: ignore
        assert "line5" in out
        assert "line7" in out
        assert "line9" in out

    @staticmethod
    def test_show_not_found():
        console = Console(file=StringIO(), width=80, color_system=None)
        ui = RichShowConvoUI(console=console)

        ui.show_not_found("missing_id")

        out = console.file.getvalue()  # type: ignore
        assert "missing_id" in out
