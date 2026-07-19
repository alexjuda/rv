from pydantic import BaseModel


class _GHErrorItem(BaseModel):
    message: str
    type: str | None = None
    path: list[str] | None = None


class _GHGraphQLEnvelope(BaseModel):
    data: dict | None = None
    errors: list[_GHErrorItem] | None = None


class _GHActor(BaseModel):
    login: str


class _GHFindPRNode(BaseModel):
    number: int


class _GHFindPRPullRequests(BaseModel):
    nodes: list[_GHFindPRNode] | None = None


class _GHFindPRRepo(BaseModel):
    pullRequests: _GHFindPRPullRequests | None = None


class _GHFindPRData(BaseModel):
    repository: _GHFindPRRepo | None = None


class _GHPageInfo(BaseModel):
    hasNextPage: bool
    endCursor: str | None = None


class _GHPRNode(BaseModel):
    number: int
    title: str
    author: _GHActor | None = None
    url: str
    baseRefName: str
    headRefName: str
    state: str
    headRefOid: str


class _GHPRListPullRequests(BaseModel):
    nodes: list[_GHPRNode] | None = None
    pageInfo: _GHPageInfo | None = None


class _GHPRListRepo(BaseModel):
    pullRequests: _GHPRListPullRequests | None = None


class _GHPRListData(BaseModel):
    repository: _GHPRListRepo | None = None


class _GHCommit(BaseModel):
    oid: str


class _GHComment(BaseModel):
    id: str
    author: _GHActor | None = None
    body: str
    createdAt: str


class _GHCommentConnection(BaseModel):
    nodes: list[_GHComment] | None = None


class _GHReview(BaseModel):
    id: str
    author: _GHActor | None = None
    body: str
    createdAt: str
    state: str
    commit: _GHCommit | None = None


class _GHReviewConnection(BaseModel):
    nodes: list[_GHReview] | None = None


class _GHThreadComment(BaseModel):
    id: str
    body: str
    author: _GHActor | None = None
    createdAt: str


class _GHThreadCommentConnection(BaseModel):
    nodes: list[_GHThreadComment] | None = None


class _GHReviewThread(BaseModel):
    id: str
    isResolved: bool | None = None
    path: str | None = None
    line: int | None = None
    comments: _GHThreadCommentConnection | None = None


class _GHReviewThreadConnection(BaseModel):
    nodes: list[_GHReviewThread] | None = None


class _GHFullPR(BaseModel):
    url: str
    title: str
    author: _GHActor | None = None
    baseRefName: str
    headRefName: str
    state: str
    headRefOid: str
    comments: _GHCommentConnection | None = None
    reviews: _GHReviewConnection | None = None
    reviewThreads: _GHReviewThreadConnection | None = None


class _GHFullPRRepo(BaseModel):
    pullRequest: _GHFullPR | None = None


class _GHFullPRData(BaseModel):
    repository: _GHFullPRRepo | None = None
