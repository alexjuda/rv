from collections.abc import Sequence

from rich.console import Console
from rich.table import Table

from ...domain.models.convo import ListEntry, ListEntryState, ThreadSummary


class TextListConvoUI:
    def show_list(self, entries: Sequence[ListEntry]) -> None:
        console = Console()
        table = Table()

        table.add_column("ID")
        table.add_column("Location")
        table.add_column("Author")
        table.add_column("State")
        table.add_column("Body")
        table.add_column("Replies")

        for entry in entries:
            table.add_row(
                entry.id,
                entry.location,
                entry.author,
                self._format_state(entry.state),
                entry.body_excerpt[:60],
                self._format_thread(entry.thread_summary),
            )

        console.print(table)

    @staticmethod
    def _format_state(state: ListEntryState) -> str:
        match state:
            case None:
                return ""
            case "unresolved":
                return "unresolved"
            case "resolved":
                return "resolved"
            case "approved":
                return "approved"
            case "changes_requested":
                return "changes requested"
            case "commented":
                return "commented"

    @staticmethod
    def _format_thread(thread_summary: ThreadSummary | None) -> str:
        if thread_summary is None:
            return ""
        return f"{thread_summary.n_replies}"
