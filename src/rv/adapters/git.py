from pathlib import Path

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

    def read_file(self, path: str, commit: str | None = None) -> str | None:
        try:
            if commit is not None:
                result = self._runner.stdout(["git", "show", f"{commit}:{path}"])
                return "\n".join(result)
            repo_root = Path(
                self._runner.stdout(["git", "rev-parse", "--show-toplevel"])[0]
            )
            file_path = repo_root / path
            return file_path.read_text()
        except (CmdError, FileNotFoundError, OSError):
            return None
