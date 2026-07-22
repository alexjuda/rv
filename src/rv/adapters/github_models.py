from pydantic import BaseModel


class GHErrorItem(BaseModel):
    message: str
    type: str | None = None
    path: list[str] | None = None


class GHGraphQLEnvelope(BaseModel):
    data: dict | None = None
    errors: list[GHErrorItem] | None = None


class GHActor(BaseModel):
    login: str


class GHFindPRNode(BaseModel):
    number: int


class GHFindPRPullRequests(BaseModel):
    nodes: list[GHFindPRNode] | None = None


class GHFindPRRepo(BaseModel):
    pullRequests: GHFindPRPullRequests


class GHFindPRData(BaseModel):
    repository: GHFindPRRepo | None = None


class GHPageInfo(BaseModel):
    hasNextPage: bool
    endCursor: str | None = None


class GHPRNode(BaseModel):
    number: int
    title: str
    author: GHActor | None = None
    url: str
    baseRefName: str
    headRefName: str
    state: str
    headRefOid: str


class GHPRListPullRequests(BaseModel):
    nodes: list[GHPRNode] | None = None
    pageInfo: GHPageInfo


class GHPRListRepo(BaseModel):
    pullRequests: GHPRListPullRequests


class GHPRListData(BaseModel):
    repository: GHPRListRepo | None = None


class _GHCommit(BaseModel):
    oid: str


class GHComment(BaseModel):
    id: str
    author: GHActor | None = None
    body: str
    createdAt: str


class GHCommentConnection(BaseModel):
    nodes: list[GHComment] | None = None


class GHReview(BaseModel):
    id: str
    author: GHActor | None = None
    body: str
    createdAt: str
    state: str
    commit: _GHCommit | None = None


class GHReviewConnection(BaseModel):
    nodes: list[GHReview] | None = None


class GHReviewRef(BaseModel):
    id: str


class GHThreadComment(BaseModel):
    id: str
    body: str
    author: GHActor | None = None
    createdAt: str
    pullRequestReview: GHReviewRef | None = None


class GHThreadCommentConnection(BaseModel):
    nodes: list[GHThreadComment] | None = None


class GHReviewThread(BaseModel):
    id: str
    isResolved: bool
    path: str
    line: int | None = None
    comments: GHThreadCommentConnection


class GHReviewThreadConnection(BaseModel):
    nodes: list[GHReviewThread] | None = None


class GHFullPR(BaseModel):
    url: str
    title: str
    author: GHActor | None = None
    baseRefName: str
    headRefName: str
    state: str
    headRefOid: str
    comments: GHCommentConnection
    reviews: GHReviewConnection | None = None
    reviewThreads: GHReviewThreadConnection


class GHFullPRRepo(BaseModel):
    pullRequest: GHFullPR | None = None


class GHFullPRData(BaseModel):
    repository: GHFullPRRepo | None = None
