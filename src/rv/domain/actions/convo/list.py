from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ...exceptions import PRNotCachedError
from ...models.convo import ListEntry, ThreadSummary
from ...models.github import PRLocator, Thread
from ...ports import VCS, Forge, Store
from .._resolve import resolve_pr_loc


@dataclass
class ListConvoOpts:
    pr: int | PRLocator | None = None
    all: bool = False
    unresolved: bool | None = None
    resolved: bool | None = None
    pr_comments: bool | None = None
    reviews: bool | None = None
    file: str | None = None


class ListConvoUI(Protocol):
    def show_list(self, entries: Sequence[ListEntry]) -> None:
        """
        Display a table of conversation entries.
        """


def _parse_created_at(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def _build_thread_summary(thread: "Thread") -> ThreadSummary:
    replies = thread.comments[1:]
    seen: list[str] = []
    for c in replies:
        if c.author not in seen:
            seen.append(c.author)
    return ThreadSummary(n_replies=len(replies), reply_authors=seen)


@dataclass
class _ActiveFilters:
    unresolved: bool
    resolved: bool
    pr_comments: bool
    reviews: bool


class ListConvo:
    def __init__(self, store: Store, forge: Forge, vcs: VCS, ui: ListConvoUI):
        self._store = store
        self._forge = forge
        self._vcs = vcs
        self._ui = ui

    async def exec(self, opts: ListConvoOpts) -> None:
        pr_loc = await resolve_pr_loc(opts.pr, vcs=self._vcs, forge=self._forge)

        full_pr = self._store.get_pr(pr_loc)
        if full_pr is None:
            raise PRNotCachedError(pr_loc)

        filters = self._active_filters(opts)
        convo = full_pr.convo

        entries: list[ListEntry] = []
        for thread in convo.threads:
            if thread.is_resolved:
                if not filters.resolved:
                    continue
            else:
                if not filters.unresolved:
                    continue
            tc = thread.comments[0]
            thread_summary = (
                _build_thread_summary(thread) if len(thread.comments) > 1 else None
            )
            entries.append(
                ListEntry(
                    id=thread.id,
                    location=f"{thread.path}:{thread.line}",
                    author=tc.author,
                    state="unresolved" if not thread.is_resolved else "resolved",
                    body_excerpt=tc.body,
                    thread_summary=thread_summary,
                    created_at=tc.created_at,
                )
            )

        if filters.pr_comments:
            entries.extend(
                ListEntry(
                    id=comment.id,
                    location="(general)",
                    author=comment.author,
                    state=None,
                    body_excerpt=comment.body,
                    thread_summary=None,
                    created_at=_parse_created_at(comment.created_at),
                )
                for comment in convo.pr_comments
            )

        if filters.reviews:
            entries.extend(
                ListEntry(
                    id=review.id,
                    location="(general)",
                    author=review.author,
                    state=review.state,
                    body_excerpt=review.body,
                    thread_summary=None,
                    created_at=_parse_created_at(review.created_at),
                )
                for review in convo.reviews
            )

        entries.sort(key=lambda e: e.created_at)

        self._ui.show_list(entries)

    @staticmethod
    def _active_filters(opts: ListConvoOpts) -> _ActiveFilters:
        if opts.all:
            return _ActiveFilters(
                unresolved=True,
                resolved=True,
                pr_comments=True,
                reviews=True,
            )

        return _ActiveFilters(
            unresolved=True if opts.unresolved is None else opts.unresolved,
            resolved=False if opts.resolved is None else opts.resolved,
            pr_comments=False if opts.pr_comments is None else opts.pr_comments,
            reviews=False if opts.reviews is None else opts.reviews,
            **(
                {"pr_comments": False, "reviews": False}
                if opts.file is not None
                else {}
            ),
        )
