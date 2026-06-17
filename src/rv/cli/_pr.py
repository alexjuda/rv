import asyncio
from typing import Annotated

from typer import Argument, Typer

from ..domain.actions.pr.list import PRList
from ..domain.actions.pull import Pull
from ._deps import CLIDeps
from ._opt_parser import parse_pr_ref
from .ui.pr_list import TextPRListUI
from .ui.pull import TextPullUI

app = Typer()


@app.command()
def list():
    deps = CLIDeps()
    action = PRList(
        store=deps.store,
        ui=TextPRListUI(),
    )

    action.exec()


@app.command()
def pull(
    pr: Annotated[
        str | None,
        Argument(
            help="PR to pull. Supported formats: `42`, `#42`, `owner/repo#42`",
            show_default="infer from current git branch and origin",
        ),
    ] = None,
):
    deps = CLIDeps()
    action = Pull(
        store=deps.store,
        vcs=deps.vcs,
        forge=deps.forge,
        ui=TextPullUI(),
    )

    pr_arg = parse_pr_ref(pr)

    async def _run():
        await action.exec(pr_arg=pr_arg)

    asyncio.run(_run())
