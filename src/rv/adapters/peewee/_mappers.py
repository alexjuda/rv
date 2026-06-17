# type: ignore
# Peewee descriptor access (row.owner, row.threads, etc.) can't be
# statically resolved. This module quarantines all such access so the
# rest of the adapter can be fully type-checked.

from ...domain.models.github import (
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
from .models import (
    PRCommentModel,
    PRModel,
    ReviewModel,
    ThreadCommentModel,
    ThreadModel,
)


def row_to_full_pr(row: PRModel) -> FullPR:
    return FullPR(
        pr=PR(
            locator=PRLocator(RepoLocator(row.owner, row.repo), row.number),
            url=row.url,
            title=row.title,
            author=row.author,
            base_branch=row.base_branch,
            head_branch=row.head_branch,
            state=row.state,
            latest_commit=row.latest_commit,
        ),
        convo=PRConversation(
            threads=[thread_to_domain(t) for t in row.threads],
            pr_comments=[pr_comment_to_domain(c) for c in row.pr_comments],
            reviews=[review_to_domain(r) for r in row.reviews],
        ),
    )


def thread_to_domain(t: ThreadModel) -> Thread:
    return Thread(
        id=t.id,
        is_resolved=t.is_resolved,
        path=t.path,
        line=t.line,
        comments=[thread_comment_to_domain(c) for c in t.comments],
    )


def thread_comment_to_domain(c: ThreadCommentModel) -> ThreadComment:
    return ThreadComment(id=c.id, body=c.body, author=c.author, created_at=c.created_at)


def pr_comment_to_domain(c: PRCommentModel) -> PRComment:
    return PRComment(id=c.id, author=c.author, body=c.body, created_at=c.created_at)


def review_to_domain(r: ReviewModel) -> Review:
    return Review(
        id=r.id,
        author=r.author,
        body=r.body,
        created_at=r.created_at,
        state=r.state,
        commit=r.commit,
    )
