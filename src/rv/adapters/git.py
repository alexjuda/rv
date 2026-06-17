from ..domain.exceptions import GitError
from .runner import CmdError, ProcRunner


class Git:
    def __init__(self, runner: ProcRunner):
        self._runner = runner

    def get_current_branch(self) -> str:
        try:
            return self._runner.stdout(["git", "branch", "--show-current"])[0]
        except CmdError as e:
            raise GitError("failed to get current branch") from e

    def get_current_commit(self) -> str:
        try:
            return self._runner.stdout(["git", "rev-parse", "HEAD"])[0]
        except CmdError as e:
            raise GitError("failed to get current commit") from e

    def get_origin(self) -> str:
        try:
            return self._runner.stdout(["git", "remote", "get-url", "origin"])[0]
        except CmdError as e:
            raise GitError("failed to get origin") from e
