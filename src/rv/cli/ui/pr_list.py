from datetime import UTC, datetime

import humanize
from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text

from ...domain.models.actions import PRList, PRListCategorized, PRListEntry


class TextPRListUI:
    def show_categorized(self, pr_list: PRListCategorized) -> None: ...

    def show_all(self, pr_list: PRList) -> None:
        console = Console()
        table = Table()

        table.add_column("PR #")
        table.add_column("Title")
        table.add_column("Author")
        table.add_column("Summary")
        table.add_column("Synced?")

        for entry in pr_list:
            table.add_row(
                f"#{entry.pr_number}",
                entry.title,
                Text(entry.author, style=Style(dim=True))
                if entry.author is not None
                else Text("[deleted]", style=Style(dim=True)),
                self.summary(entry),
                self.sync_status(entry),
            )

        console.print(table)

    @staticmethod
    def summary(entry: PRListEntry) -> Text:
        """
        Heuristics for showing actionable information only.
        """
        components = []

        n_unactioned = entry.n_unresolved_threads - entry.n_pending_thread_comments

        if (n := n_unactioned) > 0:
            components.append(f"{n} unresolved")

        if (n := entry.n_pending_thread_comments) > 0:
            components.append(f"{n} pending replies")

        match entry.effective_review_state:
            case "approved":
                components.append("✓ approved")
            case "changes_requested":
                components.append("✗ changes requested")
            case "commented":
                pass
            case None:
                components.append("no traction yet")

        return Text(", ".join(components))

    @staticmethod
    def sync_status(entry: PRListEntry, now: datetime | None = None) -> Text:
        if entry.n_pending_thread_comments > 0:
            return Text("not pushed")

        if now is None:
            now = datetime.now(UTC)

        if entry.is_stale:
            delta = humanize.naturaldelta(now - entry.last_synced_at)
            return Text(f"stale ({delta})")

        return Text(
            humanize.naturaltime(
                entry.last_synced_at,
                when=now,
            )
        )
