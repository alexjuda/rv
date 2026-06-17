from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import peewee
from peewee import SqliteDatabase

from ...domain.models.github import FullPR, PRLocator, Thread, ThreadComment
from ...domain.models.storage import StoredPR, SyncMeta
from ._mappers import row_to_full_pr, thread_comment_to_domain, thread_to_domain
from .models import (
    MODELS,
    PRCommentModel,
    PRModel,
    ReviewModel,
    ThreadCommentModel,
    ThreadModel,
    db,
)


class PeeweeStore:
    def __init__(self, db: SqliteDatabase):
        self._db = db

    @staticmethod
    def open(db_path: str = ".rv/rv.db") -> PeeweeStore:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(exist_ok=True, parents=True)

        db.init(db_path, pragmas={"journal_mode": "wal", "foreign_keys": 1})
        db.connect()
        db.create_tables(MODELS)
        return PeeweeStore(db)

    def get_pr(self, pr: PRLocator) -> FullPR | None:
        try:
            row = (
                PRModel.select()
                .where(
                    PRModel.owner == pr.repo.owner,
                    PRModel.repo == pr.repo.repo,
                    PRModel.number == pr.number,
                )
                .get()
            )
        except peewee.DoesNotExist:
            return None
        return row_to_full_pr(row)

    def store_pr(self, pr: FullPR) -> None:
        loc = pr.pr.locator
        now = datetime.now(UTC)

        with self._db.atomic():
            row, created = PRModel.get_or_create(
                owner=loc.repo.owner,
                repo=loc.repo.repo,
                number=loc.number,
                defaults={
                    "url": pr.pr.url,
                    "title": pr.pr.title,
                    "author": pr.pr.author,
                    "base_branch": pr.pr.base_branch,
                    "head_branch": pr.pr.head_branch,
                    "state": pr.pr.state,
                    "latest_commit": pr.pr.latest_commit,
                    "synced_at": now,
                },
            )
            if not created:
                row.url = pr.pr.url
                row.title = pr.pr.title
                row.author = pr.pr.author
                row.base_branch = pr.pr.base_branch
                row.head_branch = pr.pr.head_branch
                row.state = pr.pr.state
                row.latest_commit = pr.pr.latest_commit
                row.synced_at = now
                row.save()

            ThreadModel.delete().where(ThreadModel.pr == row).execute()
            for t in pr.convo.threads:
                thread_row = ThreadModel.create(
                    id=t.id,
                    pr=row,
                    is_resolved=t.is_resolved,
                    path=t.path,
                    line=t.line,
                )
                if t.comments:
                    ThreadCommentModel.insert_many(
                        [
                            {
                                "id": c.id,
                                "thread": thread_row.id,
                                "body": c.body,
                                "author": c.author,
                                "created_at": c.created_at,
                            }
                            for c in t.comments
                        ]
                    ).execute()

            PRCommentModel.delete().where(PRCommentModel.pr == row).execute()
            if pr.convo.pr_comments:
                PRCommentModel.insert_many(
                    [
                        {
                            "id": c.id,
                            "pr": row.id,
                            "author": c.author,
                            "body": c.body,
                            "created_at": c.created_at,
                        }
                        for c in pr.convo.pr_comments
                    ]
                ).execute()

            ReviewModel.delete().where(ReviewModel.pr == row).execute()
            if pr.convo.reviews:
                ReviewModel.insert_many(
                    [
                        {
                            "id": r.id,
                            "pr": row.id,
                            "author": r.author,
                            "body": r.body,
                            "created_at": r.created_at,
                            "state": r.state,
                            "commit": r.commit,
                        }
                        for r in pr.convo.reviews
                    ]
                ).execute()

    def get_threads_matching(self, id_prefix: str) -> list[Thread]:
        rows = ThreadModel.select().where(ThreadModel.id.startswith(id_prefix))
        return [thread_to_domain(r) for r in rows]

    def get_thread_comments_matching(self, id_prefix: str) -> list[ThreadComment]:
        rows = ThreadCommentModel.select().where(
            ThreadCommentModel.id.startswith(id_prefix)
        )
        return [thread_comment_to_domain(r) for r in rows]

    def get_thread(self, id: str) -> Thread | None:
        try:
            row = ThreadModel.get_by_id(id)
        except peewee.DoesNotExist:
            return None
        return thread_to_domain(row)

    def get_thread_comment(self, id: str) -> ThreadComment | None:
        try:
            row = ThreadCommentModel.get_by_id(id)
        except peewee.DoesNotExist:
            return None
        return thread_comment_to_domain(row)

    def list_prs(self) -> list[StoredPR]:
        rows = PRModel.select()
        return [
            StoredPR(
                pr=row_to_full_pr(row),
                meta=SyncMeta(synced_at=row.synced_at),
            )
            for row in rows
        ]

    def count_prs(self) -> int:
        return PRModel.select().count()

    def count_threads_prs(self, resolved: bool) -> tuple[int, int]:
        matching = ThreadModel.select().where(ThreadModel.is_resolved == resolved)
        return matching.count(), matching.select(ThreadModel.pr).distinct().count()
