"""
Entities and value objects for PR data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class ThreadComment:
    id: str  # opaque, provided by forge
    body: str
    author: str
    created_at: datetime


@dataclass
class Thread:
    id: str  # opaque, provided by forge
    is_resolved: bool
    path: str
    line: int
    commit_sha: str
    comments: list[ThreadComment]


@dataclass
class PRComment:
    id: str  # opaque, provided by forge
    author: str
    body: str
    created_at: datetime


type ReviewState = Literal["approved", "changes_requested", "commented"]


@dataclass
class Review:
    id: str  # opaque, provided by forge
    author: str
    body: str
    created_at: datetime
    state: ReviewState
    commit: str


type PRState = Literal["open", "closed", "merged"]


@dataclass
class RepoLocator:
    owner: str
    repo: str


@dataclass
class PRLocator:
    repo: RepoLocator
    number: int

    @property
    def full_name(self) -> str:
        return f"{self.repo.owner}/{self.repo.repo}#{self.number}"


@dataclass
class PR:
    locator: PRLocator
    url: str
    title: str
    author: str
    base_branch: str
    head_branch: str
    state: PRState
    latest_commit: str


@dataclass
class PRConversation:
    """
    Aggregate value object.
    """

    threads: list[Thread]
    pr_comments: list[PRComment]
    reviews: list[Review]


@dataclass
class FullPR:
    """
    Aggregate value object.
    """

    pr: PR
    convo: PRConversation
