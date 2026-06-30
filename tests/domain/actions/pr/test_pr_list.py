from datetime import UTC, datetime
from unittest.mock import create_autospec

from pytest import fixture

from rv.domain.actions.pr.list import PRList, PRListUI, _build_entry
from rv.domain.models.github import (
    PR,
    FullPR,
    PRConversation,
    PRLocator,
    PRState,
    RepoLocator,
    Review,
    Thread,
)
from rv.domain.models.storage import StoredPR, SyncMeta
from rv.domain.ports import Store

_SAMPLE_DT = datetime.fromisoformat("2026-06-27T19:51:12+02:00")


def _stored(
    number: int = 42,
    title: str = "title",
    author: str | None = None,
    state: PRState = "open",
    threads: list[Thread] | None = None,
    reviews: list[Review] | None = None,
    synced_at: datetime = _SAMPLE_DT,
) -> StoredPR:
    return StoredPR(
        pr=FullPR(
            pr=PR(
                locator=PRLocator(RepoLocator("owner", "repo"), number),
                url=f"github.com/owner/repo/pulls/{number}",
                title=title,
                author=author,
                base_branch="main",
                head_branch="feat",
                state=state,
                latest_commit="abc",
            ),
            convo=PRConversation(
                threads=threads or [],
                pr_comments=[],
                reviews=reviews or [],
            ),
        ),
        meta=SyncMeta(synced_at=synced_at),
    )


# --- mock fixtures ---


@fixture
def store():
    return create_autospec(Store)


@fixture
def ui():
    return create_autospec(PRListUI)


@fixture
def action(store, ui):
    return PRList(store=store, ui=ui)


# --- _build_entry unit tests ---


class TestBuildEntry:
    @staticmethod
    def test_author_from_pr():
        entry = _build_entry(_stored(author="alice"))
        assert entry.author == "alice"

    @staticmethod
    def test_author_none_when_missing():
        entry = _build_entry(_stored())
        assert entry.author is None

    @staticmethod
    def test_pr_number_and_title():
        entry = _build_entry(_stored(number=7, title="my pr"))
        assert entry.pr_number == 7
        assert entry.title == "my pr"

    @staticmethod
    def test_pr_state():
        entry = _build_entry(_stored(state="merged"))
        assert entry.pr_state == "merged"

    @staticmethod
    def test_no_threads_yields_zero_unresolved():
        entry = _build_entry(_stored(threads=[]))
        assert entry.n_unresolved_threads == 0

    @staticmethod
    def test_unresolved_threads_counted():
        thread = Thread(
            id="1", is_resolved=False, path="x", line=1, commit_sha="c", comments=[]
        )
        entry = _build_entry(_stored(threads=[thread]))
        assert entry.n_unresolved_threads == 1

    @staticmethod
    def test_resolved_threads_ignored():
        thread = Thread(
            id="1", is_resolved=True, path="x", line=1, commit_sha="c", comments=[]
        )
        entry = _build_entry(_stored(threads=[thread]))
        assert entry.n_unresolved_threads == 0

    @staticmethod
    def test_multiple_unresolved_threads_summed():
        threads = [
            Thread(
                id="1", is_resolved=False, path="x", line=1, commit_sha="c", comments=[]
            ),
            Thread(
                id="2", is_resolved=True, path="y", line=2, commit_sha="d", comments=[]
            ),
            Thread(
                id="3", is_resolved=False, path="z", line=3, commit_sha="e", comments=[]
            ),
        ]
        entry = _build_entry(_stored(threads=threads))
        assert entry.n_unresolved_threads == 2

    @staticmethod
    def test_no_reviews_yields_none():
        entry = _build_entry(_stored(reviews=[]))
        assert entry.effective_review_state is None

    @staticmethod
    def test_changes_requested_review_state():
        reviews = [
            Review(
                id="1",
                author="b",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="changes_requested",
                commit="c",
            )
        ]
        entry = _build_entry(_stored(reviews=reviews))
        assert entry.effective_review_state == "changes_requested"

    @staticmethod
    def test_approved_review_state():
        reviews = [
            Review(
                id="1",
                author="b",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="approved",
                commit="c",
            )
        ]
        entry = _build_entry(_stored(reviews=reviews))
        assert entry.effective_review_state == "approved"

    @staticmethod
    def test_commented_review_state():
        reviews = [
            Review(
                id="1",
                author="b",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="commented",
                commit="c",
            )
        ]
        entry = _build_entry(_stored(reviews=reviews))
        assert entry.effective_review_state == "commented"

    @staticmethod
    def test_changes_requested_highest_priority():
        reviews = [
            Review(
                id="1",
                author="a",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="commented",
                commit="c",
            ),
            Review(
                id="2",
                author="b",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="approved",
                commit="c",
            ),
            Review(
                id="3",
                author="c",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="changes_requested",
                commit="c",
            ),
        ]
        entry = _build_entry(_stored(reviews=reviews))
        assert entry.effective_review_state == "changes_requested"

    @staticmethod
    def test_approved_overrides_commented():
        reviews = [
            Review(
                id="1",
                author="a",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="commented",
                commit="c",
            ),
            Review(
                id="2",
                author="b",
                body="",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                state="approved",
                commit="c",
            ),
        ]
        entry = _build_entry(_stored(reviews=reviews))
        assert entry.effective_review_state == "approved"

    @staticmethod
    def test_last_synced_at_mapped():
        synced_at = datetime.fromisoformat("2026-06-25T10:00:00+00:00")
        entry = _build_entry(_stored(synced_at=synced_at))
        assert entry.last_synced_at == synced_at

    @staticmethod
    def test_is_stale_placeholder():
        entry = _build_entry(_stored())
        assert entry.is_stale is False

    @staticmethod
    def test_n_pending_thread_comments_placeholder():
        entry = _build_entry(_stored())
        assert entry.n_pending_thread_comments == 0


# --- exec integration tests ---


class TestExec:
    @staticmethod
    def test_passes_built_entries_to_show_all(store, ui, action):
        stored = _stored(number=42, title="add user authentication")
        store.list_prs.return_value = [stored]

        action.exec()

        ui.show_all.assert_called_once()
        entries = ui.show_all.call_args[0][0]
        assert len(entries) == 1
        assert entries[0].pr_number == 42
        assert entries[0].title == "add user authentication"

    @staticmethod
    def test_empty_store_passes_empty_list(store, ui, action):
        store.list_prs.return_value = []

        action.exec()

        ui.show_all.assert_called_once_with([])
