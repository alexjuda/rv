import pytest
from unittest.mock import patch, MagicMock
from rv.git import (
    get_current_branch,
    get_current_commit,
    is_git_repo,
    parse_github_remote,
    GitError,
    NotAGitRepoError,
    DetachedHeadError,
)


class TestIsGitRepo:
    @staticmethod
    def test_is_git_repo_true():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = is_git_repo()
            assert result is True

    @staticmethod
    def test_is_git_repo_false():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128)
            result = is_git_repo()
            assert result is False


class TestGetCurrentBranch:
    @staticmethod
    def test_get_current_branch_success():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="feature/test\n")
            result = get_current_branch()
            assert result == "feature/test"

    @staticmethod
    def test_not_a_git_repo():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128, stderr="fatal: not a git repository"
            )
            with pytest.raises(NotAGitRepoError):
                get_current_branch()

    @staticmethod
    def test_detached_head():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="HEAD detached at abc123\n"
            )
            with pytest.raises(DetachedHeadError):
                get_current_branch()

    @staticmethod
    def test_no_branch():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            with pytest.raises(GitError, match="cannot determine branch"):
                get_current_branch()


class TestGetCurrentCommit:
    @staticmethod
    def test_get_current_commit_success():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="abc1234def5678901\n"
            )
            result = get_current_commit()
            assert result == "abc1234def5678901"

    @staticmethod
    def test_get_current_commit_strips_whitespace():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="  abc1234def5678901  \n"
            )
            result = get_current_commit()
            assert result == "abc1234def5678901"

    @staticmethod
    def test_get_current_commit_failure():
        with patch("rv.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            with pytest.raises(GitError):
                get_current_commit()


class TestParseGitHubRemote:
    @staticmethod
    def test_parse_ssh_url():
        result = parse_github_remote("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")

    @staticmethod
    def test_parse_ssh_url_no_suffix():
        result = parse_github_remote("git@github.com:owner/repo")
        assert result == ("owner", "repo")

    @staticmethod
    def test_parse_https_url():
        result = parse_github_remote("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    @staticmethod
    def test_parse_https_url_no_suffix():
        result = parse_github_remote("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    @staticmethod
    def test_parse_invalid_url():
        result = parse_github_remote("https://gitlab.com/owner/repo")
        assert result is None

    @staticmethod
    def test_parse_invalid_no_repo():
        result = parse_github_remote("git@github.com:owner")
        assert result is None
