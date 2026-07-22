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


@dataclass
class ReviewSummary:
    n_posted_threads: int
    state: ReviewState
    comment_empty: bool


@dataclass
class ListEntry:
    id: str
    type: ListEntryType
    location: str | None
    author: str | None
    state: ListEntryState
    body_excerpt: str
    # TODO: delete this
    thread_summary: ThreadSummary | None
    summary: ThreadSummary | ReviewSummary | None
    created_at: datetime
