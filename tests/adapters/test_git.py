"""
Integration tests for the Git adapter.

These tests use real git repos in temporary directories rather than mocking ProcRunner. The value of
the Git adapter is constructing correct git subcommand syntax and parsing their stdout, which is
only testable against a real .git repo.
"""

from pathlib import Path

from pytest import MonkeyPatch, fixture, raises

from rv.adapters.git import Git
from rv.adapters.runner import ProcRunner
from rv.domain.exceptions import GitError


@fixture
def git_env(tmp_path: Path, monkeypatch: MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    return Git(ProcRunner())


@fixture
def runner():
    return ProcRunner()


@fixture
def init_git(git_env: Git, runner: ProcRunner):
    runner.stdout(["git", "init"])
    runner.stdout(["git", "config", "--local", "user.email", "test@test.com"])
    runner.stdout(["git", "config", "--local", "user.name", "Test"])
    return git_env


@fixture
def git_with_commit(init_git: Git, runner: ProcRunner):
    Path("file.txt").write_text("hello")
    runner.stdout(["git", "add", "."])
    runner.stdout(["git", "commit", "-m", "init"])
    return init_git


@fixture
def git_with_origin(init_git: Git, runner: ProcRunner):
    runner.stdout(["git", "remote", "add", "origin", "git@github.com:owner/repo.git"])
    return init_git


class TestGit:
    class TestGetCurrentBranch:
        @staticmethod
        def test_returns_branch_name(git_with_commit: Git):
            branch = git_with_commit.get_current_branch()
            assert branch == "main"

        @staticmethod
        def test_raises_error_outside_repo(git_env: Git):
            with raises(GitError, match="failed to get current branch"):
                git_env.get_current_branch()

    class TestGetCurrentCommit:
        @staticmethod
        def test_returns_commit_hash(git_with_commit: Git):
            commit = git_with_commit.get_current_commit()
            assert len(commit) == 40
            assert commit.isalnum()

        @staticmethod
        def test_raises_error_outside_repo(git_env: Git):
            with raises(GitError, match="failed to get current commit"):
                git_env.get_current_commit()

    class TestGetOrigin:
        @staticmethod
        def test_returns_origin_url(git_with_origin: Git):
            origin = git_with_origin.get_origin()
            assert origin == "git@github.com:owner/repo.git"

        @staticmethod
        def test_raises_error_no_remote(init_git: Git):
            with raises(GitError, match="failed to get origin"):
                init_git.get_origin()

        @staticmethod
        def test_raises_error_outside_repo(git_env: Git):
            with raises(GitError, match="failed to get origin"):
                git_env.get_origin()
