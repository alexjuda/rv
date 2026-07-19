import asyncio
from typing import Annotated

from typer import Argument, Typer

from ..domain.actions.complete_ids import CompleteIDs
from ..domain.actions.show import Show
from ..domain.actions.status import Status
from ._convo import app as convo_app
from ._deps import CLIDeps
from ._pr import app as pr_app
from .ui.show import TextCompleteIDsUI, TextShowUI
from .ui.status import TextStatusUI

app = Typer(
    no_args_is_help=True,
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(convo_app, name="convo")
app.add_typer(pr_app, name="pr")


def _complete_commentish_ids(prefix: str) -> list[tuple[str, str]]:
    deps = CLIDeps()
    action = CompleteIDs(store=deps.store, ui=TextCompleteIDsUI())
    return action.exec(prefix)


@app.command()
def show(
    id: Annotated[
        str, Argument(help="Comment ID", autocompletion=_complete_commentish_ids)
    ],
):
    deps = CLIDeps()
    action = Show(
        store=deps.store,
        ui=TextShowUI(),
    )

    async def _run():
        await action.exec(id=id)

    asyncio.run(_run())


@app.command()
def status():
    deps = CLIDeps()
    action = Status(store=deps.store, ui=TextStatusUI())
    action.exec()


if __name__ == "__main__":
    app()
