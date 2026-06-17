import os

from .runner import CmdError, ProcRunner


class AuthProvider:
    def __init__(self, runner: ProcRunner):
        self._runner = runner

    def get_token(self) -> str:
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            return token

        try:
            lines = self._runner.stdout(["gh", "auth", "token"])
        except CmdError:
            raise ValueError(
                "No GitHub token found. Set GITHUB_TOKEN or make sure `gh auth token` works"
            )
        return lines[0]

    def validate_token(self, token: str):
        pass
