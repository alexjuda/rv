from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .github import ReviewState

type ListEntryState = (
    Literal["unresolved", "resolved", "approved", "changes_requested", "commented"]
    | None
)

type ListEntryType = Literal["thread", "pr_comment", "review"]


@dataclass
class ThreadSummary:
    n_replies: int
    reply_authors: list[str]
    is_resolved: bool


@dataclass
class ReviewSummary:
    n_posted_threads: int
    state: ReviewState
    comment_empty: bool


@dataclass
class PRCommentSummary:
    # Empty because we don't need to convey any additional information over that someone posed a PR comment.
    pass


@dataclass
class ListEntry:
    id: str
    type: ListEntryType
    location: str | None
    author: str | None
    body_excerpt: str
    summary: ThreadSummary | ReviewSummary | PRCommentSummary
    created_at: datetime
