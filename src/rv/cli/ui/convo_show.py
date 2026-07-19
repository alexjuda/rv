from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from ...domain.actions.convo.show import CodeContext
from ...domain.models.github import PRComment, PRLocator, Review, Thread


def _format_pr(pr_loc: PRLocator) -> str:
    return pr_loc.full_name


def _format_date(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y")


def _n_replies(thread: Thread) -> int:
    return len(thread.comments) - 1


class RichShowConvoUI:
    def __init__(self, console: Console | None = None):
        self._console = console or Console()

    def show_thread(
        self,
        thread: Thread,
        pr_loc: PRLocator | None,
        context: CodeContext | None,
    ) -> None:
        header_text = Text()
        if pr_loc is not None:
            header_text.append(f"{_format_pr(pr_loc)}  ·  ", style="bold")
        header_text.append(f"{thread.path}:{thread.line}")
        resolved = "resolved" if thread.is_resolved else "unresolved"
        n_replies = _n_replies(thread)
        replies_text = f"{n_replies} replies"
        header_text.append(f"  ·  {resolved}  ·  {replies_text}")

        self._console.print(Panel(header_text, expand=True))

        if context is not None:
            lexer = Syntax.guess_lexer(path=context.path)
            syntax = Syntax(
                "\n".join(context.lines),
                lexer,
                line_numbers=True,
                start_line=context.start_line,
                highlight_lines={context.target_line},
            )
            self._console.print(syntax)
            self._console.print()

        for i, comment in enumerate(thread.comments):
            if i > 0:
                self._console.print()
            self._console.print(
                Rule(
                    Text(f" @{comment.author}, {_format_date(comment.created_at)}"),
                    style="dim",
                )
            )
            self._console.print(comment.body)

    def show_pr_comment(self, comment: PRComment, pr_loc: PRLocator) -> None:
        header_text = Text()
        header_text.append(f"{_format_pr(pr_loc)}  ·  ", style="bold")
        header_text.append(f"@{comment.author}, {_format_date(comment.created_at)}")
        self._console.print(Panel(header_text, expand=True))
        self._console.print(comment.body)

    def show_review(self, review: Review, pr_loc: PRLocator) -> None:
        header_text = Text()
        header_text.append(f"{_format_pr(pr_loc)}  ·  ", style="bold")
        header_text.append(f"@{review.author}, {_format_date(review.created_at)}")
        header_text.append(f"  ·  {review.state.upper()}")
        self._console.print(Panel(header_text, expand=True))
        self._console.print(review.body)

    def show_pr_conversation(
        self,
        pr_comments: list[PRComment],
        reviews: list[Review],
        pr_loc: PRLocator,
    ) -> None:
        summary_text = Text()
        summary_text.append(f"{_format_pr(pr_loc)}", style="bold")
        summary_text.append(
            f"  ·  {len(pr_comments)} comments  ·  {len(reviews)} reviews"
        )
        self._console.print(Panel(summary_text, expand=True))
        self._console.print()

        for i, item in enumerate(
            sorted([*pr_comments, *reviews], key=lambda x: x.created_at)
        ):
            if i > 0:
                self._console.print()
            header_text = Text()
            header_text.append(f"@{item.author}, {_format_date(item.created_at)}")
            if isinstance(item, Review):
                header_text.append(f"  ·  {item.state.upper()}")
            self._console.print(Panel(header_text, expand=True))
            self._console.print(item.body)

    def show_not_found(self, id: str) -> None:
        self._console.print(f"[yellow]Not found: {id}[/yellow]")
