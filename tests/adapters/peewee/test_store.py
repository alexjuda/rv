from datetime import datetime

from peewee import SqliteDatabase
from pytest import fixture, mark

from rv.adapters.peewee import PeeweeStore
from rv.adapters.peewee.models import MODELS
from rv.domain.models.github import (
    PR,
    FullPR,
    PRConversation,
    PRLocator,
    RepoLocator,
    Review,
    Thread,
    ThreadComment,
)


class TestPeeweeStore:
    @fixture
    @staticmethod
    def store():
        db = SqliteDatabase(":memory:")
        db.bind(MODELS, bind_refs=False, bind_backrefs=False)
        db.connect()
        db.create_tables(MODELS)
        yield PeeweeStore(db)
        db.close()

    class TestGetPR:
        @staticmethod
        def test_empty(store: PeeweeStore, sample_pr_locator: PRLocator):
            assert store.get_pr(sample_pr_locator) is None

        @staticmethod
        def test_roundtrip(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            stored = store.get_pr(sample_full_pr.pr.locator)
            assert stored == sample_full_pr

    class TestGetThread:
        @staticmethod
        def test_empty(store: PeeweeStore):
            assert store.get_thread("nonexistent") is None

        @staticmethod
        def test_after_store(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            thread_id = sample_full_pr.convo.threads[0].id
            stored = store.get_thread(thread_id)
            assert stored == sample_full_pr.convo.threads[0]

    class TestGetThreadsMatching:
        @staticmethod
        def test_empty(store: PeeweeStore):
            assert store.get_threads_matching("anything") == []

        @staticmethod
        def test_matches_prefix(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            results = store.get_threads_matching("PR")
            assert results == [sample_full_pr.convo.threads[0]]

        @staticmethod
        def test_matches_subset(store: PeeweeStore):
            pr = FullPR(
                pr=PR(
                    locator=PRLocator(RepoLocator("owner", "repo"), 1),
                    url="url",
                    title="title",
                    author="someone",
                    base_branch="main",
                    head_branch="feat",
                    state="open",
                    latest_commit="abc",
                ),
                convo=PRConversation(
                    threads=[
                        Thread(
                            id="a-1",
                            is_resolved=False,
                            path="a.py",
                            line=1,
                            commit_sha="abc",
                            review_id=None,
                            comments=[],
                        ),
                        Thread(
                            id="a-2",
                            is_resolved=False,
                            path="a.py",
                            line=2,
                            commit_sha="abc",
                            review_id=None,
                            comments=[],
                        ),
                        Thread(
                            id="b-1",
                            is_resolved=True,
                            path="b.py",
                            line=1,
                            commit_sha="abc",
                            review_id=None,
                            comments=[],
                        ),
                    ],
                    pr_comments=[],
                    reviews=[],
                ),
            )
            store.store_pr(pr)
            results = store.get_threads_matching("a-")
            assert results == pr.convo.threads[:2]

    class TestGetThreadCommentsMatching:
        @staticmethod
        def test_empty(store: PeeweeStore):
            assert store.get_thread_comments_matching("anything") == []

        @staticmethod
        def test_matches_prefix(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            results = store.get_thread_comments_matching("2")
            assert results == [sample_full_pr.convo.threads[0].comments[0]]

        @staticmethod
        def test_matches_subset(store: PeeweeStore):
            now = datetime.fromisoformat("2024-01-01T13:34:12+01:00")
            pr = FullPR(
                pr=PR(
                    locator=PRLocator(RepoLocator("owner", "repo"), 1),
                    url="url",
                    title="title",
                    author="someone",
                    base_branch="main",
                    head_branch="feat",
                    state="open",
                    latest_commit="abc",
                ),
                convo=PRConversation(
                    threads=[
                        Thread(
                            id="t-1",
                            is_resolved=False,
                            path="a.py",
                            line=1,
                            commit_sha="abc",
                            review_id=None,
                            comments=[
                                ThreadComment(
                                    id="c-1", body="x", author="me", created_at=now
                                ),
                                ThreadComment(
                                    id="c-2", body="y", author="me", created_at=now
                                ),
                                ThreadComment(
                                    id="d-1", body="z", author="me", created_at=now
                                ),
                            ],
                        ),
                    ],
                    pr_comments=[],
                    reviews=[],
                ),
            )
            store.store_pr(pr)
            results = store.get_thread_comments_matching("c-")
            assert results == pr.convo.threads[0].comments[:2]

    class TestGetThreadComment:
        @staticmethod
        def test_empty(store: PeeweeStore):
            assert store.get_thread_comment("nonexistent") is None

        @staticmethod
        def test_after_store(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            comment_id = sample_full_pr.convo.threads[0].comments[0].id
            stored = store.get_thread_comment(comment_id)
            assert stored == sample_full_pr.convo.threads[0].comments[0]

    class TestListPRs:
        @staticmethod
        def test_empty(store: PeeweeStore):
            assert store.list_prs() == []

        @staticmethod
        def test_after_store(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            stored = store.list_prs()
            assert len(stored) == 1
            stored_pr = stored[0]
            assert stored_pr.pr == sample_full_pr
            assert stored_pr.meta.synced_at is not None

    class TestCountPRs:
        @staticmethod
        def test_empty(store: PeeweeStore):
            assert store.count_prs() == 0

        @staticmethod
        def test_after_store(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            assert store.count_prs() == 1

    class TestCountThreadsPRs:
        @staticmethod
        @mark.parametrize("resolved", [False, True])
        def test_empty(store: PeeweeStore, resolved: bool):
            assert store.count_threads_prs(resolved=resolved) == (0, 0)

        @staticmethod
        def test_after_store(store: PeeweeStore, sample_full_pr: FullPR):
            store.store_pr(sample_full_pr)
            assert store.count_threads_prs(resolved=False) == (1, 1)
            assert store.count_threads_prs(resolved=True) == (0, 0)

    class TestGetPRLocatorForThread:
        @staticmethod
        def test_returns_none_for_nonexistent_thread(store: PeeweeStore):
            assert store.get_pr_locator_for_thread("nonexistent") is None

        @staticmethod
        def test_returns_locator_for_stored_thread(
            store: PeeweeStore, sample_full_pr: FullPR
        ):
            store.store_pr(sample_full_pr)
            loc = store.get_pr_locator_for_thread("PR_1")
            assert loc == sample_full_pr.pr.locator

    class TestThreadReviewLink:
        @staticmethod
        def test_roundtrip_with_review_id(store: PeeweeStore):
            now = datetime.fromisoformat("2024-01-01T13:34:12+01:00")
            review = Review(
                id="rv_1",
                author="bob",
                body="LGTM",
                created_at=now,
                state="approved",
                commit="abc123",
            )
            thread = Thread(
                id="t_linked",
                is_resolved=False,
                path="a.py",
                line=10,
                commit_sha="abc",
                review_id="rv_1",
                comments=[],
            )
            pr = FullPR(
                pr=PR(
                    locator=PRLocator(RepoLocator("owner", "repo"), 1),
                    url="url",
                    title="title",
                    author="someone",
                    base_branch="main",
                    head_branch="feat",
                    state="open",
                    latest_commit="abc",
                ),
                convo=PRConversation(
                    threads=[thread],
                    pr_comments=[],
                    reviews=[review],
                ),
            )
            store.store_pr(pr)
            stored = store.get_thread("t_linked")
            assert stored is not None
            assert stored.review_id == "rv_1"

        @staticmethod
        def test_roundtrip_without_review_id(
            store: PeeweeStore, sample_full_pr: FullPR
        ):
            store.store_pr(sample_full_pr)
            stored = store.get_thread("PR_1")
            assert stored is not None
            assert stored.review_id is None
