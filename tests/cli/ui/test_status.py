from pytest import CaptureFixture, fixture

from rv.cli.ui.status import TextStatusUI
from rv.domain.models.actions import CollectionStat, StatusSummary, ThreadStat


class TestTextStatusUI:
    @fixture
    @staticmethod
    def ui():
        return TextStatusUI()

    @staticmethod
    def test_full_data(
        sample_status_summary: StatusSummary, ui: TextStatusUI, capsys: CaptureFixture
    ):
        ui.show_summary(sample_status_summary)

        out: str = capsys.readouterr().out
        lines = out.splitlines()
        assert len(lines) >= 5

        assert "10 PRs" in lines[0]

        assert "3 stale PRs" in out

        assert "Pending changes:" in out
        assert "new comments" in out
        assert "...across 8 PRs." in out

        assert "Work:" in out
        assert "unresolved threads" in out

    @staticmethod
    def test_all_clear(ui: TextStatusUI, capsys: CaptureFixture):
        summary = StatusSummary(
            stored_n_prs=3,
            stale_n_prs=0,
            pending_comments_stat=CollectionStat.empty(),
            pending_threads_stat=ThreadStat.empty(),
            pending_n_prs=0,
            unresolved_n_threads=0,
            unresolved_n_prs=0,
            unreviewed_n_prs=0,
            reviewed_n_prs=3,
        )
        ui.show_summary(summary)

        out: str = capsys.readouterr().out
        lines = out.splitlines()

        assert "3 PRs" in lines[0]

        assert "stale PRs" not in out.lower()
        assert "pending changes:" not in out.lower()
