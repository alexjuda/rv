from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ...exceptions import PRNotCachedError
from ...models.convo import ListEntry, PRCommentSummary, ReviewSummary, ThreadSummary
from ...models.github import PRComment, PRLocator, Review, Thread
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
    file: Path | None = None


@dataclass
class ReviewWithThreads:
    review: Review
    threads: list[Thread]


class ListConvoUI(Protocol):
    def show_list(self, entries: Sequence[ListEntry]) -> None:
        """
        Display a table of conversation entries.
        """


@dataclass
class _ActiveFilters:
    unresolved: bool
    resolved: bool
    pr_comments: bool
    reviews: bool
    # Inline thread file prefix filter.
    file: Path | None


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

        reviews_with_threads = self._combine_reviews_with_threads(
            convo.reviews, convo.threads
        )

        entries: list[ListEntry] = [
            *self._populate_threads(convo.threads, filters=filters),
            *self._populate_pr_comments(convo.pr_comments, filters=filters),
            *self._populate_reviews(reviews_with_threads, filters=filters),
        ]

        entries.sort(key=lambda e: e.created_at)

        self._ui.show_list(entries)

    @staticmethod
    def _active_filters(opts: ListConvoOpts) -> _ActiveFilters:
        if opts.all:
            return _ActiveFilters(
                unresolved=True,
                resolved=True,
                # Theoretically, a user can type '--all --file path/to/file.py'. We should allow showing all
                # comments regardless of their status related to that file or directory.
                pr_comments=(opts.file is None),
                reviews=(opts.file is None),
                file=opts.file,
            )

        return _ActiveFilters(
            unresolved=True if opts.unresolved is None else opts.unresolved,
            resolved=False if opts.resolved is None else opts.resolved,
            pr_comments=False
            if opts.file is not None
            else (False if opts.pr_comments is None else opts.pr_comments),
            reviews=False
            if opts.file is not None
            else (False if opts.reviews is None else opts.reviews),
            file=opts.file,
        )

    @staticmethod
    def _comment_matches_path(
        thread_path: str | None, filter_path: Path | None
    ) -> bool:
        if thread_path is None:
            # No thread path => it's a general comment => always matches.
            return True

        if filter_path is None:
            # No filter => always matches.
            return True

        path_str = str(filter_path)
        if thread_path == path_str:
            return True
        prefix = path_str.rstrip("/") + "/"
        return thread_path.startswith(prefix)

    @staticmethod
    def _build_thread_summary(thread: "Thread") -> ThreadSummary:
        replies = thread.comments[1:]
        seen: list[str] = []
        for c in replies:
            if c.author is not None and c.author not in seen:
                seen.append(c.author)
        return ThreadSummary(
            n_replies=len(replies), reply_authors=seen, is_resolved=thread.is_resolved
        )

    @classmethod
    def _populate_threads(
        cls, threads: list[Thread], /, filters: _ActiveFilters
    ) -> Iterable[ListEntry]:
        """
        Table rows coming from comment threads.
        """
        for thread in threads:
            if not cls._comment_matches_path(thread.path, filters.file):
                continue

            if thread.is_resolved:
                if not filters.resolved:
                    continue
            else:
                if not filters.unresolved:
                    continue
            tc = thread.comments[0]
            thread_summary = cls._build_thread_summary(thread)
            yield ListEntry(
                id=thread.id,
                type="thread",
                location=f"{thread.path}:{thread.line}",
                author=tc.author,
                body_excerpt=tc.body,
                summary=thread_summary,
                created_at=tc.created_at,
            )

    @staticmethod
    def _populate_pr_comments(
        comments: list[PRComment], filters: _ActiveFilters
    ) -> Iterable[ListEntry]:
        """
        Table rows coming from PR (issue) comments.
        """
        if not filters.pr_comments:
            return

        for comment in comments:
            yield ListEntry(
                id=comment.id,
                type="pr_comment",
                location=None,
                author=comment.author,
                body_excerpt=comment.body,
                summary=PRCommentSummary(),
                created_at=comment.created_at,
            )

    @staticmethod
    def _populate_reviews(
        reviews: list[ReviewWithThreads], filters: _ActiveFilters
    ) -> Iterable[ListEntry]:
        """
        Table rows coming from PR reviews.
        """
        if not filters.reviews:
            return

        for review in reviews:
            yield ListEntry(
                id=review.review.id,
                type="review",
                location=None,
                author=review.review.author,
                body_excerpt=review.review.body,
                summary=ReviewSummary(
                    n_posted_threads=len(review.threads),
                    state=review.review.state,
                    comment_empty=review.review.body == "",
                ),
                created_at=review.review.created_at,
            )

    @staticmethod
    def _combine_reviews_with_threads(
        reviews: list[Review], threads: list[Thread]
    ) -> list[ReviewWithThreads]:
        # Theoretically we could get this association at the DB level, in the adapter. However that would lead
        # to a proliferation of data types across the application. Resolving the review<->threads mapping
        # in-memory here is a much simpler solution. We don't have to care about performance, it's all gonna be
        # small amounts of data anyway.
        threads_by_review_id: dict[str, list[Thread]] = {}
        for thread in threads:
            if thread.review_id is None:
                # Skip inline comment threads detached from PR reviews.
                continue
            threads_by_review_id.setdefault(thread.review_id, []).append(thread)

        return [
            ReviewWithThreads(
                review=review,
                threads=threads_by_review_id.get(review.id, []),
            )
            for review in reviews
        ]
