from collections.abc import Sequence

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ...domain.models.convo import ListEntry, ListEntryState, ThreadSummary, ReviewSummary


class TextListConvoUI:
    def show_list(self, entries: Sequence[ListEntry]) -> None:
        console = Console()
        table = Table()

        table.add_column("ID")
        table.add_column("Location")
        table.add_column("Author")
        table.add_column("State")
        table.add_column("Body")
        table.add_column("Summary")

        for entry in entries:
            table.add_row(
                entry.id,
                entry.location,
                Text(entry.author) if entry.author is not None else Text("[deleted]"),
                self._format_state(entry.state),
                entry.body_excerpt,
                self._format_summary(entry.summary),
            )

        console.print(table)

    @staticmethod
    def _format_state(state: ListEntryState) -> str:
        # We only show thread states in the "state" column. PR-level stuff is in the "summary" column.
        match state:
            case None:
                return ""
            case "unresolved":
                # Thread
                return "unresolved"
            case "resolved":
                # Thread
                return "resolved"
            case "approved":
                # PR
                return ""
            case "changes_requested":
                # PR
                return ""
            case "commented":
                # PR
                return ""

    @staticmethod
    def _format_summary(summary: ReviewSummary | ThreadSummary | None) -> str:
        match summary:
            case None:
                return ""
            case ThreadSummary():
                if (n := summary.n_replies) == 1:
                    return f"+{n} reply"
                else:
                    return f"+{n} replies"
            case ReviewSummary():
                components = []

                match summary.state:
                    case "approved":
                        components.append("[A]")
                    case "changes_requested":
                        components.append("[CR]")
                    case "commented":
                        if summary.comment_empty:
                            components.append("reviewed")
                        if not summary.comment_empty:
                            components.append("[C]")

                if (n := summary.n_posted_threads) > 0:
                    if n == 1:
                        components.append(f"+{n} thread")
                    else:
                        components.append(f"+{n} threads")
                return ", ".join(components)
