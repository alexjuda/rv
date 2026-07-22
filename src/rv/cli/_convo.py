from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

from typer import Argument, Option, Typer

from ..domain.actions.complete_ids import CompleteIDs
from ..domain.actions.convo.list import ListConvo, ListConvoOpts
from ..domain.actions.convo.show import ShowConvo
from ._deps import CLIDeps
from ._opt_parser import parse_pr_ref
from .ui.convo import TextListConvoUI
from .ui.convo_show import RichShowConvoUI
from .ui.show import TextCompleteIDsUI

app = Typer(no_args_is_help=True)


@app.command()
def list(
    pr: Annotated[
        str | None,
        Argument(
            help="PR to list. Supported formats: `42`, `#42`, `owner/repo#42`",
            show_default="infer from current git branch and origin",
        ),
    ] = None,
    all: Annotated[
        bool,
        Option(help="Show all conversation items including resolved threads"),
    ] = False,
    unresolved: Annotated[
        bool | None,
        Option(help="Show unresolved threads"),
    ] = None,
    resolved: Annotated[
        bool | None,
        Option(help="Show resolved threads"),
    ] = None,
    pr_comments: Annotated[
        bool | None,
        Option(help="Show PR-level comments"),
    ] = None,
    reviews: Annotated[
        bool | None,
        Option(help="Show review comments"),
    ] = None,
    file: Annotated[
        Path | None,
        Option(help="Filter by file path"),
    ] = None,
):
    deps = CLIDeps()
    action = ListConvo(
        store=deps.store,
        forge=deps.forge,
        vcs=deps.vcs,
        ui=TextListConvoUI(),
    )

    opts = ListConvoOpts(
        pr=parse_pr_ref(pr),
        all=all,
        unresolved=unresolved,
        resolved=resolved,
        pr_comments=pr_comments,
        reviews=reviews,
        file=file,
    )

    async def _run():
        await action.exec(opts=opts)

    asyncio.run(_run())


def _complete_thread_ids(prefix: str) -> Sequence[tuple[str, str]]:
    deps = CLIDeps()
    action = CompleteIDs(store=deps.store, ui=TextCompleteIDsUI())
    return action.exec(prefix)


@app.command()
def show(
    id: Annotated[
        str,
        Argument(
            help="Thread/comment/review ID or PR ref (#42) to display",
            autocompletion=_complete_thread_ids,
        ),
    ],
    context: Annotated[
        int,
        Option("--context", help="Lines of code context around the comment"),
    ] = 5,
):
    deps = CLIDeps()
    action = ShowConvo(
        store=deps.store,
        vcs=deps.vcs,
        forge=deps.forge,
        ui=RichShowConvoUI(),
    )
    action.exec(id=id, context_lines=context)
