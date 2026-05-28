from typing import Any, Protocol

import httpx

from rv.auth import get_token
from rv.models import PR, Thread, Comment


class GitHubError(Exception):
    pass


class RateLimitedError(GitHubError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s")


class InvalidTokenError(GitHubError):
    pass


class MissingScopeError(GitHubError):
    pass


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_API_URL = "https://api.github.com"


def _get_in(data: dict, *keys: str) -> dict | list | None:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


class ReviewProvider(Protocol):
    def get_pr_for_branch(self, owner: str, repo: str, branch: str) -> PR | None: ...

    def get_threads(self, owner: str, repo: str, pr_number: int) -> list[Thread]: ...

    def get_thread(
        self, owner: str, repo: str, pr_number: int, thread_id: str
    ) -> Thread | None: ...

    def post_reply(
        self, owner: str, repo: str, pr_number: int, thread_id: str, body: str
    ) -> str: ...

    def resolve_thread(
        self, owner: str, repo: str, pr_number: int, thread_id: str
    ) -> bool: ...


class GitHubClient:
    def __init__(self, token: str | None = None):
        self._token = token or get_token()
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        self._client = httpx.Client()

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        response = self._client.request(method, url, headers=self._headers, **kwargs)

        if response.status_code == 401:
            raise InvalidTokenError("token rejected by GitHub — run `rv auth login`")
        if response.status_code == 403:
            error_data = response.json()
            if "missing" in error_data["message"].lower():
                raise MissingScopeError(error_data["message"])
            raise GitHubError(error_data.get("message", "Forbidden"))
        if response.status_code == 429:
            retry_after = int(response.headers.get("X-RateLimit-Reset", 0))
            raise RateLimitedError(retry_after)

        response.raise_for_status()
        return response

    def get_pr_for_branch(self, owner: str, repo: str, branch: str) -> PR | None:
        query = """
        query($owner: String!, $repo: String!, $branch: String!) {
            repository(owner: $owner, name: $repo) {
                pullRequests(headRefName: $branch, first: 10, states: OPEN) {
                    nodes {
                        number
                        title
                        headRefName
                        baseRefName
                        state
                        url
                    }
                }
            }
        }
        """
        variables = {"owner": owner, "repo": repo, "branch": branch}
        response = self._request(
            "POST", GITHUB_GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        data: dict[str, Any] = response.json()

        pr_nodes = _get_in(data, "data", "repository", "pullRequests", "nodes") or []
        if not pr_nodes:
            return None

        pr = pr_nodes[0]
        return PR(
            number=pr["number"],
            title=pr["title"],
            url=pr["url"],
            base_branch=pr["baseRefName"],
            head_branch=pr["headRefName"],
            state=pr["state"].lower(),
        )

    def _review_threads_query(self, owner: str, repo: str, pr_number: int) -> dict:
        query = """
        query($owner: String!, $repo: String!, $pr: Int!) {
            repository(owner: $owner, name: $repo) {
                pullRequest(number: $pr) {
                    reviewThreads(first: 100) {
                        nodes {
                            id
                            path
                            line
                            startLine
                            isResolved
                            isOutdated
                            comments(first: 100) {
                                nodes {
                                    id
                                    body
                                    author { login }
                                    createdAt
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"owner": owner, "repo": repo, "pr": pr_number}
        response = self._request(
            "POST", GITHUB_GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        return response.json()

    def get_threads(self, owner: str, repo: str, pr_number: int) -> list[Thread]:
        data: dict[str, Any] = self._review_threads_query(owner, repo, pr_number)

        thread_nodes = (
            _get_in(data, "data", "repository", "pullRequest", "reviewThreads", "nodes")
            or []
        )

        threads = []
        for rt in thread_nodes:
            comments = [
                Comment(
                    id=c["id"],
                    body=c["body"],
                    author=c["author"]["login"],
                    created_at=c["createdAt"],
                )
                for c in rt["comments"]["nodes"]
            ]
            threads.append(
                Thread(
                    id=rt["id"],
                    file=rt["path"],
                    line=rt.get("line"),
                    start_line=rt.get("startLine"),
                    resolved=rt["isResolved"],
                    outdated=rt["isOutdated"],
                    comments=comments,
                )
            )
        return threads

    def get_thread(
        self, owner: str, repo: str, pr_number: int, thread_id: str
    ) -> Thread | None:
        data: dict[str, Any] = self._review_threads_query(owner, repo, pr_number)

        thread_nodes = (
            _get_in(data, "data", "repository", "pullRequest", "reviewThreads", "nodes")
            or []
        )

        for rt in thread_nodes:
            if rt["id"] == thread_id:
                comments = [
                    Comment(
                        id=c["id"],
                        body=c["body"],
                        author=c["author"]["login"],
                        created_at=c["createdAt"],
                    )
                    for c in rt["comments"]["nodes"]
                ]
                return Thread(
                    id=rt["id"],
                    file=rt["path"],
                    line=rt.get("line"),
                    start_line=rt.get("startLine"),
                    resolved=rt["isResolved"],
                    outdated=rt["isOutdated"],
                    comments=comments,
                )
        return None

    def post_reply(
        self, owner: str, repo: str, pr_number: int, thread_id: str, body: str
    ) -> str:
        mutation = """
        mutation($input: AddPullRequestReviewThreadInput!) {
            addPullRequestReviewThread(input: $input) {
                thread { id }
            }
        }
        """
        input_data = {"pullRequestId": f"PR:{owner}:{repo}:{pr_number}", "body": body}
        variables = {"input": input_data}
        response = self._request(
            "POST", GITHUB_GRAPHQL_URL, json={"query": mutation, "variables": variables}
        )
        data = response.json()
        return data["data"]["addPullRequestReviewThread"]["thread"]["id"]

    def resolve_thread(
        self, owner: str, repo: str, pr_number: int, thread_id: str
    ) -> bool:
        mutation = """
        mutation($input: MarkPullRequestReviewThreadResolvedInput!) {
            markPullRequestReviewThreadResolved(input: $input) {
                clientMutationId
            }
        }
        """
        input_data = {
            "threadId": thread_id,
        }
        variables = {"input": input_data}
        response = self._request(
            "POST", GITHUB_GRAPHQL_URL, json={"query": mutation, "variables": variables}
        )
        return response.status_code == 200


def create_provider() -> ReviewProvider:
    return GitHubClient()
