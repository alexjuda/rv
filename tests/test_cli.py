from contextlib import contextmanager
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from rv.cache import CacheStore
from rv.cli import RepoContext, cli, check_head_mismatch, ensure_fresh_cache
from rv.models import Comment, Meta, PR, State, Thread


@contextmanager
def _with_no_remote():
    with patch("rv.cli.is_git_repo", return_value=True):
        with patch("rv.cli.get_current_branch", return_value="main"):
            with patch("rv.cli.get_remote_origin", return_value=None):
                yield


class TestCLI:
    @staticmethod
    def test_help_via_minus_h():
        runner = CliRunner()
        result = runner.invoke(cli, ["-h"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    @staticmethod
    def test_subcommand_help_via_minus_h():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with _with_no_remote():
                result = runner.invoke(cli, ["status", "-h"])
                assert result.exit_code == 0
                assert "Usage:" in result.output

    @staticmethod
    def test_status_command_exists():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with _with_no_remote():
                result = runner.invoke(cli, ["status"])
        assert result.exit_code != 0
        assert "no remote origin" in result.output

    @staticmethod
    def test_status_shows_last_synced():
        runner = CliRunner()
        mock_cache = MagicMock()
        mock_cache.list_threads.return_value = [
            Thread(
                id="thread_0",
                file="file0.py",
                line=10,
                start_line=5,
                resolved=False,
                outdated=False,
                comments=[
                    Comment(
                        id="c0",
                        body="review comment body",
                        author="reviewer",
                        created_at="2026-05-13T10:00:00Z",
                    )
                ],
            )
        ]
        mock_cache.read_state.return_value = None
        mock_cache.read_meta.return_value = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-23T12:00:00Z",
            synced_at_commit="abc",
            pr=PR(
                number=1,
                title="Test PR",
                url="https://github.com/owner/repo/pull/1",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )

        repo_ctx = RepoContext(
            owner="owner",
            repo="repo",
            pr_number=1,
            pr=PR(
                number=1,
                title="Test PR",
                url="https://github.com/owner/repo/pull/1",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )

        with patch("rv.cli.check_head_mismatch"):
            result = runner.invoke(
                cli,
                ["status"],
                obj={"repo_context": repo_ctx, "cache": mock_cache},
            )
        assert result.exit_code == 0, result.output
        assert "last synced" in result.output.lower(), result.output
        assert "2026-05-23" in result.output, result.output

    @staticmethod
    def test_list_command_exists():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with _with_no_remote():
                result = runner.invoke(cli, ["list"])
        assert result.exit_code != 0
        assert "no remote origin" in result.output

    @staticmethod
    def _make_repo_ctx(owner="owner", repo="repo", pr_number=1):
        return RepoContext(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            pr=PR(
                number=pr_number,
                title="Test PR",
                url=f"https://github.com/{owner}/{repo}/pull/{pr_number}",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )

    @staticmethod
    def _make_thread(tid, file, line, resolved=False, body="comment"):
        return Thread(
            id=tid,
            file=file,
            line=line,
            start_line=line - 5,
            resolved=resolved,
            outdated=False,
            comments=[
                Comment(
                    id=tid,
                    body=body,
                    author="reviewer",
                    created_at="2026-05-13T10:00:00Z",
                )
            ],
        )

    @staticmethod
    def test_list_marks_current_thread_with_arrow():
        runner = CliRunner()
        mock_cache = MagicMock()
        mock_cache.list_threads.return_value = [
            TestCLI._make_thread(f"thread_{i}", f"file{i}.py", i * 10) for i in range(4)
        ]
        mock_cache.read_state.return_value = State(current_thread_id="thread_0")

        with patch("rv.cli.check_head_mismatch"):
            result = runner.invoke(
                cli,
                ["list"],
                obj={
                    "repo_context": TestCLI._make_repo_ctx(),
                    "cache": mock_cache,
                },
            )
        assert result.exit_code == 0, result.output
        assert "> thread_0" in result.output, result.output

    @staticmethod
    def test_list_does_not_mark_when_no_current_thread():
        runner = CliRunner()
        mock_cache = MagicMock()
        mock_cache.list_threads.return_value = [
            TestCLI._make_thread(f"thread_{i}", f"file{i}.py", i * 10) for i in range(2)
        ]
        mock_cache.read_state.return_value = None

        with patch("rv.cli.check_head_mismatch"):
            result = runner.invoke(
                cli,
                ["list"],
                obj={
                    "repo_context": TestCLI._make_repo_ctx(),
                    "cache": mock_cache,
                },
            )
        assert result.exit_code == 0, result.output
        assert "> " not in result.output, result.output

    @staticmethod
    def test_next_command_exists():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with _with_no_remote():
                result = runner.invoke(cli, ["next"])
        assert result.exit_code != 0
        assert "no remote origin" in result.output

    @staticmethod
    def test_show_command_exists():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with _with_no_remote():
                result = runner.invoke(cli, ["show"])
        assert result.exit_code != 0
        assert "no remote origin" in result.output

    @staticmethod
    def test_pull_command_exists():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with _with_no_remote():
                result = runner.invoke(cli, ["pull"])
        assert result.exit_code != 0
        assert "no remote origin" in result.output

    @staticmethod
    def test_auth_login_no_keyring():
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "login", "test_token"])
        assert result.exit_code in [0, 1]

    @staticmethod
    def test_auth_status_shows_env_detail():
        runner = CliRunner()
        with patch("rv.cli.auth_status") as mock_auth:
            mock_auth.return_value = {
                "source": "env",
                "has_token": True,
                "mechanism": "$GITHUB_TOKEN env var",
            }
            result = runner.invoke(cli, ["auth", "status"])
            assert result.exit_code == 0
            assert "Token source" in result.output
            assert "$GITHUB_TOKEN" in result.output

    @staticmethod
    def test_auth_status_no_token():
        runner = CliRunner()
        with patch("rv.cli.auth_status") as mock_auth:
            mock_auth.return_value = {
                "source": None,
                "has_token": False,
                "mechanism": None,
            }
            result = runner.invoke(cli, ["auth", "status"])
            assert result.exit_code == 0
            assert "Not logged in" in result.output

    @staticmethod
    def test_auth_logout():
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "logout"])
        assert result.exit_code == 0
        assert "Logged out" in result.output

    @staticmethod
    def test_lsp_command_exists():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with patch("rv.lsp.RVServer._load_context", return_value=False):
                result = runner.invoke(cli, ["lsp"])
        assert result.exit_code == 0

    @staticmethod
    def test_skip_command_removed():
        runner = CliRunner()
        result = runner.invoke(cli, ["skip"])
        assert result.exit_code != 0
        assert "no such command" in result.output.lower()

    @staticmethod
    def test_edit_command_exists():
        runner = CliRunner()
        with runner.isolated_filesystem():
            with _with_no_remote():
                result = runner.invoke(cli, ["edit"])
        assert result.exit_code != 0
        assert "no remote origin" in result.output

    @staticmethod
    def test_next_prompts_before_opening_editor_and_advances_on_no():
        runner = CliRunner()
        mock_cache = MagicMock()
        mock_cache.list_threads.return_value = [
            TestCLI._make_thread("thread_0", "file0.py", 10, body="review comment body")
        ]
        mock_cache.read_state.return_value = None

        with patch("rv.cli.check_head_mismatch"):
            with patch("rv.cli.subprocess.run") as mock_run:
                result = runner.invoke(
                    cli,
                    ["next"],
                    input="n\n",
                    obj={
                        "repo_context": TestCLI._make_repo_ctx(),
                        "cache": mock_cache,
                    },
                )
        assert result.exit_code == 0, result.output
        assert "Open $EDITOR" in result.output, result.output
        mock_run.assert_not_called()

    @staticmethod
    def test_next_opens_editor_when_user_says_yes():
        runner = CliRunner()
        mock_cache = MagicMock()
        mock_cache.list_threads.return_value = [
            TestCLI._make_thread("thread_0", "file0.py", 10, body="review comment body")
        ]
        mock_cache.read_state.return_value = None

        with patch("rv.cli.check_head_mismatch"):
            with patch("rv.cli.subprocess.run") as mock_run:
                result = runner.invoke(
                    cli,
                    ["next"],
                    input="y\n",
                    obj={
                        "repo_context": TestCLI._make_repo_ctx(),
                        "cache": mock_cache,
                    },
                )
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()

    @staticmethod
    def test_next_prints_full_thread_content():
        runner = CliRunner()
        mock_cache = MagicMock()
        mock_cache.list_threads.return_value = [
            TestCLI._make_thread("thread_0", "file0.py", 10, body="review comment body")
        ]
        mock_cache.read_state.return_value = None

        with patch("rv.cli.check_head_mismatch"):
            with patch("rv.cli.subprocess.run"):
                result = runner.invoke(
                    cli,
                    ["next"],
                    input="n\n",
                    obj={
                        "repo_context": TestCLI._make_repo_ctx(),
                        "cache": mock_cache,
                    },
                )
        assert result.exit_code == 0, result.output
        assert "reviewer" in result.output, result.output
        assert "review comment body" in result.output, result.output
        assert "file0.py:10" in result.output, result.output


class TestHeadMismatch:
    @staticmethod
    def test_warning_shows_when_commit_differs():
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc1234",
            pr=PR(
                number=1,
                title="Test PR",
                url="https://github.com/owner/repo/pull/1",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )

        with patch("rv.cli.get_current_commit", return_value="def5678"):
            with patch.object(CacheStore, "read_meta", return_value=meta):
                with patch("rv.cli.click") as mock_click:
                    check_head_mismatch("owner", "repo", 1)
                    mock_click.echo.assert_called_once()
                    output = mock_click.echo.call_args[0][0]
                    assert "abc1234" in output
                    assert "def5678" in output

    @staticmethod
    def test_no_warning_when_commit_matches():
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc1234",
            pr=PR(
                number=1,
                title="Test PR",
                url="https://github.com/owner/repo/pull/1",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )

        with patch("rv.cli.get_current_commit", return_value="abc1234"):
            with patch.object(CacheStore, "read_meta", return_value=meta):
                with patch("rv.cli.click") as mock_click:
                    check_head_mismatch("owner", "repo", 1)
                    mock_click.echo.assert_not_called()


class TestEnsureFreshCache:
    @staticmethod
    def test_auto_pull_when_stale():
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc1234",
            pr=PR(
                number=1,
                title="Test PR",
                url="https://github.com/owner/repo/pull/1",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )

        with patch.object(CacheStore, "read_meta", return_value=meta):
            with patch.object(CacheStore, "is_stale", return_value=True):
                with patch("rv.cli._run_pull") as mock_pull:
                    result = ensure_fresh_cache("owner", "repo", 1)
                    mock_pull.assert_called_once()
                    assert result is True

    @staticmethod
    def test_no_pull_when_fresh():
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc1234",
            pr=PR(
                number=1,
                title="Test PR",
                url="https://github.com/owner/repo/pull/1",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )

        with patch.object(CacheStore, "read_meta", return_value=meta):
            with patch.object(CacheStore, "is_stale", return_value=False):
                with patch("rv.cli._run_pull") as mock_pull:
                    result = ensure_fresh_cache("owner", "repo", 1)
                    mock_pull.assert_not_called()
                    assert result is False

    @staticmethod
    def test_no_pull_when_no_meta():
        with patch.object(CacheStore, "read_meta", return_value=None):
            with patch("rv.cli._run_pull") as mock_pull:
                ensure_fresh_cache("owner", "repo", 1)
                mock_pull.assert_not_called()
