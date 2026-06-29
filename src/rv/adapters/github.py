import re
from datetime import datetime
from typing import Self

import httpx

from ..domain.exceptions import InvalidOriginError
from ..domain.models.github import (
    PR,
    FullPR,
    PRComment,
    PRConversation,
    PRLocator,
    RepoLocator,
    Review,
    Thread,
    ThreadComment,
)
from ..domain.ports import Auth

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
        return resp.json()

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
        nodes = (
            data.get("data", {})
            .get("repository", {})
            .get("pullRequests", {})
            .get("nodes", [])
        )
        if not nodes:
            return None
        return PRLocator(repo=repo, number=nodes[0]["number"])

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
            pull_requests = (
                data.get("data", {}).get("repository", {}).get("pullRequests", {})
            )
            nodes = pull_requests.get("nodes", [])

            prs.extend(
                PR(
                    locator=PRLocator(repo=repo, number=node["number"]),
                    url=node["url"],
                    title=node["title"],
                    author=node["author"]["login"],
                    base_branch=node["baseRefName"],
                    head_branch=node["headRefName"],
                    state=node["state"].lower(),
                    latest_commit=node["headRefOid"],
                )
                for node in nodes
            )

            page_info = pull_requests.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            after = page_info.get("endCursor")

        return prs

    async def get_pr(self, pr: PRLocator) -> FullPR | None:
        data = await self._graphql(
            GET_PR_QUERY,
            {"owner": pr.repo.owner, "repo": pr.repo.repo, "number": pr.number},
        )
        node = data.get("data", {}).get("repository", {}).get("pullRequest")
        if not node:
            return None
        return FullPR(
            pr=PR(
                locator=pr,
                url=node["url"],
                title=node["title"],
                author=node["author"]["login"],
                base_branch=node["baseRefName"],
                head_branch=node["headRefName"],
                state=node["state"].lower(),
                latest_commit=node["headRefOid"],
            ),
            convo=PRConversation(
                threads=[
                    Thread(
                        id=t["id"],
                        is_resolved=t["isResolved"],
                        path=t["path"],
                        line=t["line"],
                        commit_sha=node["headRefOid"],
                        comments=[
                            ThreadComment(
                                id=c["id"],
                                body=c["body"],
                                author=c["author"]["login"],
                                created_at=datetime.fromisoformat(c["createdAt"]),
                            )
                            for c in t["comments"]["nodes"]
                        ],
                    )
                    for t in node["reviewThreads"]["nodes"]
                ],
                pr_comments=[
                    PRComment(
                        id=c["id"],
                        author=c["author"]["login"],
                        body=c["body"],
                        created_at=datetime.fromisoformat(c["createdAt"]),
                    )
                    for c in node["comments"]["nodes"]
                ],
                reviews=[
                    Review(
                        id=r["id"],
                        author=r["author"]["login"],
                        body=r["body"],
                        created_at=datetime.fromisoformat(r["createdAt"]),
                        state=r["state"].lower(),
                        commit=r["commit"]["oid"],
                    )
                    for r in node["reviews"]["nodes"]
                ],
            ),
        )
