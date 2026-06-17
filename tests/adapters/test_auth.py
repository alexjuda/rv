from unittest.mock import create_autospec

from pytest import MonkeyPatch, fixture, raises

from rv.adapters.auth import AuthProvider
from rv.adapters.runner import CmdError, ProcRunner


@fixture
def runner():
    return create_autospec(ProcRunner)


@fixture
def auth(runner: ProcRunner):
    return AuthProvider(runner)


class TestAuthProvider:
    @staticmethod
    def test_happy_path_env_var(monkeypatch: MonkeyPatch, auth: AuthProvider):
        monkeypatch.setenv("GITHUB_TOKEN", "foobar")

        token = auth.get_token()

        assert token

    @staticmethod
    def test_happy_path_gh_auth_token(auth: AuthProvider, runner):
        runner.stdout.return_value = "foobar"

        token = auth.get_token()

        assert token

    @staticmethod
    def test_none_available(auth: AuthProvider, runner):
        runner.stdout.side_effect = CmdError(cmd=[], stdout=b"", stderr=b"", retcode=1)

        with raises(ValueError) as err:
            _ = auth.get_token()

        assert "GITHUB_TOKEN" in err.value.args[0]
