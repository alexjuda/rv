import asyncio
from typing import Annotated

from typer import Argument, Option, Typer

from ..domain.actions.convo.list import ListConvo, ListConvoOpts
from ._deps import CLIDeps
from ._opt_parser import parse_pr_ref
from .ui.convo import TextListConvoUI

app = Typer()


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
        str | None,
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
