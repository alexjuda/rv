import re
from datetime import datetime
from typing import Self, cast

import httpx

from ..domain.exceptions import InvalidOriginError
from ..domain.models.github import (
    PR,
    FullPR,
    PRComment,
    PRConversation,
    PRLocator,
    PRState,
    RepoLocator,
    Review,
    ReviewState,
    Thread,
    ThreadComment,
)
from ..domain.ports import Auth
from .github_models import (
    _GHFindPRData,
    _GHFullPR,
    _GHFullPRData,
    _GHGraphQLEnvelope,
    _GHPRListData,
    _GHPRNode,
)

GRAPHQL_API = "https://api.github.com/graphql"

FIND_PR_QUERY = """
query($owner: String!, $repo: String!, $branch: String!) {
  repository(owner: $owner, name: $repo) {
    pullRequests(headRefName: $branch, states: [OPEN], first: 1) {
      nodes {
        number
      }
    }
  }
}
"""

GET_PR_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      url
      title
      author { login }
      baseRefName
      headRefName
      state
      headRefOid
      comments(first: 100) {
        nodes {
          id
          author { login }
          body
          createdAt
        }
      }
      reviews(first: 100) {
        nodes {
          id
          author { login }
          body
          createdAt
          state
          commit { oid }
        }
      }
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
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

LIST_REPO_PRS_QUERY = """
query($owner: String!, $repo: String!, $after: String, $states: [PullRequestState!]) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 100, states: $states, after: $after) {
      nodes {
        number
        title
        author { login }
        url
        baseRefName
        headRefName
        state
        headRefOid
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


class GitHubAPIError(Exception):
    """GitHub API response validation failed."""


class GitHub:
    def __init__(self, auth: Auth, http_client: httpx.AsyncClient | None = None):
        self._auth = auth
        self._http = http_client or httpx.AsyncClient()

    def parse_repo(self, origin: str) -> RepoLocator:
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", origin)
        if not m:
            raise InvalidOriginError(f"cannot parse origin: {origin}")
        owner, repo = m.group(1).split("/", 1)
        return RepoLocator(owner=owner, repo=repo)

    async def _graphql(self, query: str, variables: dict) -> dict:
        token = self._auth.get_token()
        resp = await self._http.post(
            GRAPHQL_API,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "rv",
            },
        )
        resp.raise_for_status()
        raw = resp.json()
        envelope = _GHGraphQLEnvelope.model_validate(raw)
        if envelope.data is None:
            if envelope.errors:
                msgs = "; ".join(e.message for e in envelope.errors)
                raise GitHubAPIError(f"GitHub API errors: {msgs}")
            raise GitHubAPIError("GitHub API returned no data")
        return envelope.data

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> None:
        await self.aclose()

    async def find_pr_for_branch(
        self, repo: RepoLocator, branch: str
    ) -> PRLocator | None:
        data = await self._graphql(
            FIND_PR_QUERY,
            {"owner": repo.owner, "repo": repo.repo, "branch": branch},
        )
        parsed = _GHFindPRData.model_validate(data)
        if parsed.repository is None:
            return None
        prs = parsed.repository.pullRequests
        if not prs.nodes:
            return None
        return PRLocator(repo=repo, number=prs.nodes[0].number)

    async def list_repo_prs(self, repo: RepoLocator, closed: bool = False) -> list[PR]:
        prs: list[PR] = []
        after: str | None = None
        states = ["OPEN", "CLOSED", "MERGED"] if closed else ["OPEN"]

        while True:
            data = await self._graphql(
                LIST_REPO_PRS_QUERY,
                {
                    "owner": repo.owner,
                    "repo": repo.repo,
                    "after": after,
                    "states": states,
                },
            )
            parsed = _GHPRListData.model_validate(data)
            if parsed.repository is None:
                break
            pull_requests = parsed.repository.pullRequests
            nodes = pull_requests.nodes or []

            prs.extend(self._to_domain_pr(repo, node) for node in nodes)

            if not pull_requests.pageInfo.hasNextPage:
                break
            after = pull_requests.pageInfo.endCursor

        return prs

    def _to_domain_pr(self, repo: RepoLocator, node: _GHPRNode) -> PR:
        return PR(
            locator=PRLocator(repo=repo, number=node.number),
            url=node.url,
            title=node.title,
            author=node.author.login if node.author else None,
            base_branch=node.baseRefName,
            head_branch=node.headRefName,
            state=cast(PRState, node.state.lower()),
            latest_commit=node.headRefOid,
        )

    async def get_pr(self, pr: PRLocator) -> FullPR | None:
        data = await self._graphql(
            GET_PR_QUERY,
            {"owner": pr.repo.owner, "repo": pr.repo.repo, "number": pr.number},
        )
        parsed = _GHFullPRData.model_validate(data)
        if parsed.repository is None or parsed.repository.pullRequest is None:
            return None
        gh_pr = parsed.repository.pullRequest
        return FullPR(
            pr=PR(
                locator=pr,
                url=gh_pr.url,
                title=gh_pr.title,
                author=gh_pr.author.login if gh_pr.author else None,
                base_branch=gh_pr.baseRefName,
                head_branch=gh_pr.headRefName,
                state=cast(PRState, gh_pr.state.lower()),
                latest_commit=gh_pr.headRefOid,
            ),
            convo=PRConversation(
                threads=self._build_threads(gh_pr),
                pr_comments=self._build_pr_comments(gh_pr),
                reviews=self._build_reviews(gh_pr),
            ),
        )

    def _build_threads(self, gh_pr: _GHFullPR) -> list[Thread]:
        threads = gh_pr.reviewThreads
        if threads.nodes is None:
            return []
        return [
            Thread(
                id=t.id,
                is_resolved=t.isResolved,
                path=t.path,
                line=t.line,
                commit_sha=gh_pr.headRefOid,
                comments=[
                    ThreadComment(
                        id=c.id,
                        body=c.body,
                        author=c.author.login if c.author else None,
                        created_at=datetime.fromisoformat(c.createdAt),
                    )
                    for c in (t.comments.nodes if t.comments.nodes else [])
                ],
            )
            for t in threads.nodes
        ]

    def _build_pr_comments(self, gh_pr: _GHFullPR) -> list[PRComment]:
        comments = gh_pr.comments
        if comments.nodes is None:
            return []
        return [
            PRComment(
                id=c.id,
                author=c.author.login if c.author else None,
                body=c.body,
                created_at=datetime.fromisoformat(c.createdAt),
            )
            for c in comments.nodes
        ]

    def _build_reviews(self, gh_pr: _GHFullPR) -> list[Review]:
        reviews = gh_pr.reviews
        if reviews is None or reviews.nodes is None:
            return []
        return [
            Review(
                id=r.id,
                author=r.author.login if r.author else None,
                body=r.body,
                created_at=datetime.fromisoformat(r.createdAt),
                state=cast(ReviewState, r.state.lower()),
                commit=r.commit.oid if r.commit else None,
            )
            for r in reviews.nodes
        ]
