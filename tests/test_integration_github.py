import pytest

from rv.auth import get_token
from rv.github import GitHubClient


@pytest.fixture
def client():
    token = get_token()
    return GitHubClient(token=token)


@pytest.mark.vcr
class TestGitHubIntegration:
    def test_get_pr_for_branch(self, client):
        pr = client.get_pr_for_branch("alexjuda", "rv-testing", "test/fixtures")
        assert pr is not None
        assert pr.number > 0
        assert pr.title is not None
        assert pr.head_branch == "test/fixtures"
        assert pr.base_branch == "main"
        assert pr.state == "open"
        assert "rv-testing" in pr.url

    def test_get_threads(self, client):
        pr = client.get_pr_for_branch("alexjuda", "rv-testing", "test/fixtures")
        assert pr is not None
        threads = client.get_threads("alexjuda", "rv-testing", pr.number)
        assert len(threads) >= 4

        unresolved = [t for t in threads if not t.resolved]
        resolved = [t for t in threads if t.resolved]
        multi_line = [
            t for t in threads if t.start_line is not None and t.start_line != t.line
        ]
        with_replies = [t for t in threads if len(t.comments) > 1]

        assert len(unresolved) >= 1
        assert len(resolved) >= 1
        assert len(multi_line) >= 1
        assert len(with_replies) >= 1

    def test_get_thread(self, client):
        pr = client.get_pr_for_branch("alexjuda", "rv-testing", "test/fixtures")
        assert pr is not None
        threads = client.get_threads("alexjuda", "rv-testing", pr.number)
        assert len(threads) >= 1

        thread = client.get_thread("alexjuda", "rv-testing", pr.number, threads[0].id)
        assert thread is not None
        assert thread.id == threads[0].id
        assert thread.file == threads[0].file

    def test_get_thread_not_found(self, client):
        pr = client.get_pr_for_branch("alexjuda", "rv-testing", "test/fixtures")
        assert pr is not None
        thread = client.get_thread(
            "alexjuda", "rv-testing", pr.number, "PRRT_nonexistent"
        )
        assert thread is None

    def test_get_pr_for_branch_no_result(self, client):
        pr = client.get_pr_for_branch(
            "alexjuda", "rv-testing", "nonexistent-branch-xyz"
        )
        assert pr is None
