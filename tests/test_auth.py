import os

import pytest
from unittest.mock import MagicMock, patch

from rv.auth import auth_status, get_token, login, logout


class TestGetToken:
    @staticmethod
    def test_env_var_priority():
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_123"}):
            token = get_token()
            assert token == "env_token_123"

    @staticmethod
    def test_keyring_fallback():
        with patch.dict(os.environ, {}, clear=True):
            with patch("rv.auth.keyring") as mock_keyring:
                mock_keyring.get_password.return_value = "keyring_token"

                token = get_token()
                assert token == "keyring_token"

    @staticmethod
    def test_gh_cli_fallback():
        with patch.dict(os.environ, {}, clear=True):
            with patch("rv.auth.keyring") as mock_keyring:
                mock_keyring.get_password.return_value = None
                with patch("rv.auth.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="gh_token\n")

                    token = get_token()
                    assert token == "gh_token"

    @staticmethod
    def test_no_token_available():
        with patch.dict(os.environ, {}, clear=True):
            with patch("rv.auth.keyring") as mock_keyring:
                mock_keyring.get_password.return_value = None
                with patch("rv.auth.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=1, stderr="not found")

                    with pytest.raises(ValueError, match="no GitHub token found"):
                        get_token()


class TestAuthCommands:
    @staticmethod
    def test_login_stores_token():
        with patch("rv.auth.keyring") as mock_keyring:
            mock_keyring.set_password.return_value = None

            login("test_token_123")
            mock_keyring.set_password.assert_called_once_with(
                "rv", "github", "test_token_123"
            )

    @staticmethod
    def test_logout_removes_token():
        with patch("rv.auth.keyring") as mock_keyring:
            mock_keyring.delete_password.return_value = None

            logout()
            mock_keyring.delete_password.assert_called_once_with("rv", "github")

    @staticmethod
    def test_status_from_keyring():
        with patch("rv.auth.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = "secret_token"

            status = auth_status()
            assert status["source"] == "keyring"
            assert status["has_token"] is True
            assert status["mechanism"] == "system keyring"

    @staticmethod
    def test_status_from_env():
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
            with patch("rv.auth.keyring") as mock_keyring:
                mock_keyring.get_password.return_value = None

                status = auth_status()
                assert status["source"] == "env"
                assert status["has_token"] is True
                assert status["mechanism"] == "$GITHUB_TOKEN env var"

    @staticmethod
    def test_status_from_gh_cli():
        with patch.dict(os.environ, {}, clear=True):
            with patch("rv.auth.keyring") as mock_keyring:
                mock_keyring.get_password.return_value = None
                with patch("rv.auth.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="gh_token\n")

                    status = auth_status()
                    assert status["source"] == "gh"
                    assert status["has_token"] is True
                    assert status["mechanism"] == "gh CLI (gh auth token)"

    @staticmethod
    def test_status_no_token():
        with patch.dict(os.environ, {}, clear=True):
            with patch("rv.auth.keyring") as mock_keyring:
                mock_keyring.get_password.return_value = None
                with patch("rv.auth.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=1)

                    status = auth_status()
                    assert status["source"] is None
                    assert status["has_token"] is False
                    assert status["mechanism"] is None
