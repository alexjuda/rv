from importlib import reload
from unittest.mock import patch

from rv.cli import ThreadDivergence
from rv.github import (
    GitHubClient,
    GitHubError,
    InvalidTokenError,
    RateLimitedError,
)


class TestGitHubClient:
    @staticmethod
    def test_uses_token():
        client = GitHubClient(token="test_token")
        assert client._token == "test_token"

    @staticmethod
    def test_with_explicit_token():
        client = GitHubClient(token="my_token")
        assert client._token == "my_token"
        assert client._headers["Authorization"] == "Bearer my_token"

    @staticmethod
    def test_github_error_exception():
        err = GitHubError("test message")
        assert str(err) == "test message"

    @staticmethod
    def test_rate_limited_error():
        err = RateLimitedError(3600)
        assert err.retry_after == 3600
        assert "Rate limited" in str(err)

    @staticmethod
    def test_invalid_token_error():
        err = InvalidTokenError("token rejected")
        assert "token rejected" in str(err)


class TestProvider:
    @staticmethod
    def test_create_provider_returns_github_client():
        with patch("rv.auth.get_token", return_value="test_token"):
            import rv.github

            reload(rv.github)
            provider = rv.github.create_provider()
            assert isinstance(provider, rv.github.GitHubClient)


class TestThreadDivergence:
    @staticmethod
    def test_divergence_deleted():
        d = ThreadDivergence(deleted=True)
        assert d.deleted is True
        assert d.resolved_by is None

    @staticmethod
    def test_divergence_resolved():
        d = ThreadDivergence(resolved_by="reviewer", has_changes=True)
        assert d.resolved_by == "reviewer"
        assert d.has_changes is True

    @staticmethod
    def test_divergence_new_comments():
        d = ThreadDivergence(new_comments=3, has_changes=True)
        assert d.new_comments == 3
        assert d.has_changes is True


class TestEdgeCases:
    """Tests for API error responses that can't be reproduced with real API calls.

    The happy-path and not-found scenarios are covered by VCR-recorded integration
    tests in test_integration_github.py. These unit tests cover edge cases like null
    fields in API responses that only occur with auth/permission errors.
    """

    @staticmethod
    def test_returns_none_when_repository_null():
        client = GitHubClient(token="test_token")

        def mock_request(method, url, **kwargs):
            class MockResponse:
                status_code = 200

                def json(self):
                    return {"data": {"repository": None}}

            return MockResponse()

        with patch.object(client, "_request", side_effect=mock_request):
            pr = client.get_pr_for_branch("owner", "repo", "feature-branch")

        assert pr is None

    @staticmethod
    def test_returns_empty_threads_when_pull_request_null():
        client = GitHubClient(token="test_token")

        def mock_request(method, url, **kwargs):
            class MockResponse:
                status_code = 200

                def json(self):
                    return {"data": {"repository": {"pullRequest": None}}}

            return MockResponse()

        with patch.object(client, "_request", side_effect=mock_request):
            threads = client.get_threads("owner", "repo", 42)

        assert threads == []


class TestResolveThread:
    @staticmethod
    def test_resolve_thread_uses_correct_mutation():
        captured_requests = []

        class MockResponse:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {
                    "data": {
                        "markPullRequestReviewThreadResolved": {"clientMutationId": "1"}
                    }
                }

        class MockClient:
            def request(self, method, url, **kwargs):
                captured_requests.append(
                    {"method": method, "url": url, "json": kwargs.get("json")}
                )
                return MockResponse()

        mock_client = MockClient()

        def _mock_request(self, method: str, url: str, **kwargs):
            return mock_client.request(method, url, **kwargs)

        with patch("rv.github.httpx.Client", return_value=mock_client):
            with patch("rv.auth.get_token", return_value="test_token"):
                with patch.object(GitHubClient, "_request", _mock_request):
                    client = GitHubClient(token="test_token")
                    client.resolve_thread("owner", "repo", 1, "PRRT_abc123")

                    assert len(captured_requests) == 1
                req = captured_requests[0]
                assert req["method"] == "POST"
                query = req["json"]["query"]
                assert "markPullRequestReviewThreadResolved" in query
                variables = req["json"]["variables"]
                assert variables["input"]["threadId"] == "PRRT_abc123"
