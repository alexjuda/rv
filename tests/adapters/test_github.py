import os
from unittest.mock import AsyncMock, Mock, create_autospec

import httpx
import pytest
import pytest_asyncio
from pytest import fixture, raises

from rv.adapters.github import GitHub, GitHubAPIError
from rv.domain.exceptions import InvalidOriginError
from rv.domain.models.github import PRLocator, RepoLocator
from rv.domain.ports import Auth


@fixture
async def github():
    auth = create_autospec(Auth)
    async with GitHub(auth=auth) as gh:
        yield gh


@pytest_asyncio.fixture
async def real_github():
    auth = create_autospec(Auth)
    auth.get_token.return_value = os.environ.get("GITHUB_TOKEN", "test")
    async with GitHub(auth=auth) as gh:
        yield gh


def _mock_graphql_client(json_response: dict) -> httpx.AsyncClient:
    mock_resp = Mock(spec=httpx.Response)
    mock_resp.raise_for_status = Mock()
    mock_resp.json = Mock(return_value=json_response)

    mock_client = create_autospec(httpx.AsyncClient, instance=True)
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


class TestGitHub:
    class TestParseRepo:
        @staticmethod
        def test_ssh_url(github: GitHub):
            result = github.parse_repo("git@github.com:owner/repo.git")
            assert result == RepoLocator(owner="owner", repo="repo")

        @staticmethod
        def test_https_url(github: GitHub):
            result = github.parse_repo("https://github.com/owner/repo.git")
            assert result == RepoLocator(owner="owner", repo="repo")

        @staticmethod
        def test_https_url_without_suffix(github: GitHub):
            result = github.parse_repo("https://github.com/owner/repo")
            assert result == RepoLocator(owner="owner", repo="repo")

        @staticmethod
        def test_invalid_origin(github: GitHub):
            with raises(InvalidOriginError):
                github.parse_repo("not-a-url")

    class TestFindPrForBranch:
        @staticmethod
        @pytest.mark.vcr
        async def test_finds_pr_for_branch(real_github: GitHub):
            repo = RepoLocator(owner="alexjuda", repo="rv-testing")
            result = await real_github.find_pr_for_branch(repo, "test/fixtures")
            assert result is not None
            assert result.repo == repo
            assert result.number > 0

        @staticmethod
        @pytest.mark.vcr
        async def test_returns_none_for_missing_branch(real_github: GitHub):
            repo = RepoLocator(owner="alexjuda", repo="rv-testing")
            result = await real_github.find_pr_for_branch(
                repo, "nonexistent-branch-xyz"
            )
            assert result is None

    class TestGetPr:
        @staticmethod
        @pytest.mark.vcr
        async def test_gets_pr_metadata(real_github: GitHub):
            repo = RepoLocator(owner="alexjuda", repo="rv-testing")
            pr_loc = PRLocator(repo=repo, number=6)
            result = await real_github.get_pr(pr_loc)

            assert result is not None
            assert result.pr.locator == pr_loc
            assert result.pr.state == "open"
            assert result.pr.base_branch == "main"
            assert result.pr.head_branch == "test/fixtures"
            assert result.pr.title
            assert result.pr.latest_commit

        @staticmethod
        @pytest.mark.vcr
        async def test_gets_pr_conversation(real_github: GitHub):
            repo = RepoLocator(owner="alexjuda", repo="rv-testing")
            result = await real_github.get_pr(PRLocator(repo=repo, number=6))
            assert result is not None

            threads = result.convo.threads
            assert isinstance(threads, list)
            if threads:
                t = threads[0]
                assert t.id
                assert isinstance(t.is_resolved, bool)
                assert t.path == "calculator.py"
                assert isinstance(t.line, int)
                for c in t.comments:
                    assert c.id
                    assert c.body
                    assert c.author
                    assert c.created_at

            reviews = result.convo.reviews
            assert isinstance(reviews, list)
            if reviews:
                r = reviews[0]
                assert r.id
                assert r.author
                assert r.created_at
                assert r.state in ("approved", "changes_requested", "commented")
                assert r.commit

            assert isinstance(result.convo.pr_comments, list)

        @staticmethod
        @pytest.mark.vcr
        async def test_returns_none_for_missing_pr(real_github: GitHub):
            repo = RepoLocator(owner="alexjuda", repo="rv-testing")
            pr_loc = PRLocator(repo=repo, number=99999)
            result = await real_github.get_pr(pr_loc)
            assert result is None

    class TestListRepoPrs:
        @staticmethod
        @pytest.mark.vcr
        async def test_lists_open_prs(real_github: GitHub):
            repo = RepoLocator(owner="alexjuda", repo="rv-testing")
            result = await real_github.list_repo_prs(repo)

            assert isinstance(result, list)
            if result:
                pr = result[0]
                assert pr.locator.number > 0
                assert pr.title
                assert pr.author
                assert pr.url
                assert pr.base_branch
                assert pr.head_branch
                assert pr.state == "open"
                assert pr.latest_commit

    class TestGraphQLErrors:
        @staticmethod
        async def test_raises_on_errors_without_data():
            auth = create_autospec(Auth)
            auth.get_token.return_value = "token"
            client = _mock_graphql_client(
                {
                    "data": None,
                    "errors": [{"message": "Not found", "type": "NOT_FOUND"}],
                }
            )
            gh = GitHub(auth=auth, http_client=client)
            with raises(GitHubAPIError, match="GitHub API errors"):
                await gh.find_pr_for_branch(RepoLocator(owner="o", repo="r"), "branch")
            await gh.aclose()

        @staticmethod
        async def test_raises_on_no_data():
            auth = create_autospec(Auth)
            auth.get_token.return_value = "token"
            client = _mock_graphql_client({"data": None})
            gh = GitHub(auth=auth, http_client=client)
            with raises(GitHubAPIError, match="no data"):
                await gh.find_pr_for_branch(RepoLocator(owner="o", repo="r"), "branch")
            await gh.aclose()

        @staticmethod
        async def test_returns_none_on_partial_results():
            auth = create_autospec(Auth)
            auth.get_token.return_value = "token"
            client = _mock_graphql_client(
                {
                    "data": {"repository": {"pullRequests": {"nodes": []}}},
                    "errors": [{"message": "irrelevant warning"}],
                }
            )
            gh = GitHub(auth=auth, http_client=client)
            result = await gh.find_pr_for_branch(
                RepoLocator(owner="o", repo="r"), "branch"
            )
            assert result is None
            await gh.aclose()
