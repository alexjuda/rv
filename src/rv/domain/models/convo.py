from dataclasses import dataclass
from datetime import datetime
from typing import Literal

type ListEntryState = (
    Literal["unresolved", "resolved", "approved", "changes_requested", "commented"]
    | None
)


@dataclass
class ThreadSummary:
    n_replies: int
    reply_authors: list[str]


@dataclass
class ListEntry:
    id: str
    location: str | None
    author: str | None
    state: ListEntryState
    body_excerpt: str
    thread_summary: ThreadSummary | None
    created_at: datetime
