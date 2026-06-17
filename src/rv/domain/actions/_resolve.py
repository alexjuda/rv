from ..exceptions import NoMatchingPRsError
from ..models.github import PRLocator
from ..ports import VCS, Forge


async def resolve_pr_loc(
    pr_arg: int | PRLocator | None, *, vcs: VCS, forge: Forge
) -> PRLocator:
    if isinstance(pr_arg, PRLocator):
        return pr_arg
    elif isinstance(pr_arg, int):
        origin = vcs.get_origin()
        repo = forge.parse_repo(origin)
        return PRLocator(repo, pr_arg)
    else:
        branch = vcs.get_current_branch()
        origin = vcs.get_origin()
        repo = forge.parse_repo(origin)
        if not (pr_loc := await forge.find_pr_for_branch(repo, branch)):
            raise NoMatchingPRsError(repo, branch)
        return pr_loc
