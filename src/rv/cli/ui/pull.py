from rich.console import Console

from ...domain.models.actions import PullSummary
from ...domain.models.github import PRLocator, RepoLocator


class TextPullUI:
    def fetching_heads_up(self, pr_loc: PRLocator):
        print(f"Fetching {self._format_pr(pr_loc)}")

    @staticmethod
    def _format_pr(pr: PRLocator) -> str:
        return pr.full_name

    def confirm(self, summary: PullSummary) -> bool:
        self.ack_summary(summary)

        resp = input("Confirm pull? [Y/n] ")
        return not resp or resp.lower() in {"y", "yes"}

    def ack_confirmation(self, saved: bool):
        if saved:
            print("Local store updated.")
        else:
            print("Skipped.")

    def ack_summary(self, summary: PullSummary):
        print(f"Fetched {self._format_pr(summary.pr_loc)}")

        something = False

        for name, stat in [
            ("inline threads", summary.stat.threads),
            ("PR comments", summary.stat.pr_comments),
            ("PR reviews", summary.stat.reviews),
        ]:
            if stat.n_new > 0:
                print(f"  {stat.n_new} new {name}")
                something = True
            if stat.n_deleted > 0:
                print(f"  {stat.n_deleted} deleted {name}")
                something = True
            if stat.n_changed > 0:
                print(f"  {stat.n_changed} edited {name}")
                something = True

        if not something:
            print("  No changes")

    def fetching_pr_list(self, repo: RepoLocator):
        print(f"Listing PRs for {repo.owner}/{repo.repo}...")

    def ack_all_done(self, ok: int, total: int):
        print(f"Pulled {ok}/{total} PR(s)")


class RichPullUI:
    def __init__(self):
        self._console = Console()
        self._n_unchanged = 0

    def fetching_heads_up(self, pr_loc: PRLocator):
        pass

    def fetching_pr_list(self, repo: RepoLocator):
        self._console.print(
            f"Pulling PRs from [bold]{repo.owner}/{repo.repo}[/bold]..."
        )

    def ack_summary(self, summary: PullSummary):
        pr = self._format_pr(summary.pr_loc)
        line = self._format_changes(summary.stat)
        if line:
            self._console.print(f"  {pr}  {line}")
        else:
            self._n_unchanged += 1

    def confirm(self, summary: PullSummary) -> bool:
        pr = self._format_pr(summary.pr_loc)
        line = self._format_changes(summary.stat)
        self._console.print(f"  {pr}  {line}")
        resp = input("  → Confirm re-fetch? [y/N]: ")
        return not resp or resp.lower() in {"y", "yes"}

    def ack_confirmation(self, saved: bool):
        if saved:
            self._console.print("  ✓ stored", style="green")
        else:
            self._console.print("  skipped", style="yellow")

    def ack_all_done(self, ok: int, total: int):
        parts = [f"Pulled [green]{ok}/{total}[/green] PR(s)"]
        if self._n_unchanged:
            parts.append(f"({self._n_unchanged} unchanged)")
        self._console.print("  ".join(parts))

    @staticmethod
    def _format_pr(pr: PRLocator) -> str:
        return pr.full_name

    @staticmethod
    def _format_changes(stat) -> str:
        parts: list[str] = []
        for name, coll in [
            ("thread", stat.threads),
            ("comment", stat.pr_comments),
            ("review", stat.reviews),
        ]:
            if coll.n_new:
                tag = name if coll.n_new == 1 else f"{name}s"
                parts.append(f"{coll.n_new} new {tag}")
            if coll.n_changed:
                tag = name if coll.n_changed == 1 else f"{name}s"
                parts.append(f"{coll.n_changed} edited {tag}")
            if coll.n_deleted:
                tag = name if coll.n_deleted == 1 else f"{name}s"
                parts.append(f"{coll.n_deleted} deleted {tag}")
        return ", ".join(parts)
