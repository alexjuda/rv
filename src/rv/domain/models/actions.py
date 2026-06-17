from dataclasses import dataclass
from datetime import datetime

from .github import PRLocator, PRState, ReviewState


@dataclass
class CollectionStat:
    """
    Like git stat but for threads, comments, etc.
    """

    n_new: int
    n_deleted: int
    n_changed: int

    @classmethod
    def empty(cls) -> "CollectionStat":
        return cls(n_new=0, n_deleted=0, n_changed=0)


@dataclass
class ConversationStat:
    """
    Aggregate for convo stats.
    """

    threads: CollectionStat
    pr_comments: CollectionStat
    reviews: CollectionStat


@dataclass
class PullSummary:
    """
    Output of the pull action.
    """

    stat: ConversationStat
    pr_loc: PRLocator


@dataclass
class ThreadStat:
    """
    For pending threads.
    """

    n_new: int
    n_deleted: int
    n_resolved: int

    @classmethod
    def empty(cls) -> "ThreadStat":
        return cls(n_new=0, n_deleted=0, n_resolved=0)


@dataclass
class StatusSummary:
    stored_n_prs: int
    "Number of PRs stored in local cache"

    stale_n_prs: int
    "Number of PRs that need re-fetching."

    pending_comments_stat: CollectionStat
    "Stats about comments off all types: inline, PR comments, review comments"

    pending_threads_stat: ThreadStat

    pending_n_prs: int
    "Number of PRs affected by pending changes."

    unresolved_n_threads: int
    unresolved_n_prs: int
    "Number of PRs affected by unresolved threads."

    unreviewed_n_prs: int
    "Number of PRs that haven't been reviewed yet."

    reviewed_n_prs: int
    "Number of PRs that received a review and need acting upon."


@dataclass
class PRListEntry:
    pr_number: int
    title: str
    author: str
    n_unresolved_threads: int

    effective_review_state: ReviewState | None
    """
    * Any approval -> A.
    * Only comments -> C.
    * Someone requested changes -> RC.
    * No reviews -> empty.
    """

    n_pending_thread_comments: int
    last_synced_at: datetime
    is_stale: bool
    pr_state: PRState


type PRList = list[PRListEntry]


@dataclass
class PRListCategorized:
    action_needed: PRList
    everything_else: PRList
