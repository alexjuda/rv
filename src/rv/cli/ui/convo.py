from collections.abc import Sequence

from rich.console import Console
from rich.table import Table

from ...domain.models.convo import (
    ListEntry,
    PRCommentSummary,
    ReviewSummary,
    ThreadSummary,
)


class TextListConvoUI:
    def show_list(self, entries: Sequence[ListEntry]) -> None:
        console = Console()
        table = Table()

        table.add_column("ID")
        table.add_column("Location")
        table.add_column("Author")
        table.add_column("Body")
        table.add_column("Summary")

        for entry in entries:
            table.add_row(
                entry.id,
                entry.location,
                entry.author or "(deleted)",
                entry.body_excerpt,
                self.format_summary(entry.summary),
            )

        console.print(table)

    @staticmethod
    def format_summary(
        summary: ReviewSummary | ThreadSummary | PRCommentSummary,
    ) -> str:
        match summary:
            case PRCommentSummary():
                return "PR comment"
            case ThreadSummary():
                text = ""

                if summary.is_resolved:
                    text += "(resolved) "

                if summary.n_replies <= 0:
                    pass
                elif (n := summary.n_replies) == 1:
                    text += f"+{n} reply"
                else:
                    text += f"+{n} replies"

                if len(summary.reply_authors) > 0:
                    text += " from "
                    text += ", ".join(f"@{a}" for a in summary.reply_authors)
                return text
            case ReviewSummary():
                components = []

                match summary.state:
                    case "approved":
                        components.append("accepted")
                    case "changes_requested":
                        components.append("requested changes")
                    case "commented":
                        if summary.comment_empty:
                            components.append("reviewed")
                        if not summary.comment_empty:
                            components.append("commented")

                if (n := summary.n_posted_threads) > 0:
                    if n == 1:
                        components.append(f"+{n} thread")
                    else:
                        components.append(f"+{n} threads")
                return ", ".join(components)
