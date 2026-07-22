from datetime import datetime
from pathlib import Path
from unittest.mock import create_autospec

from pytest import fixture, raises

from rv.domain.actions.convo.list import ListConvo, ListConvoOpts, ListConvoUI
from rv.domain.exceptions import PRNotCachedError
from rv.domain.models.convo import ListEntry, ReviewSummary, ThreadSummary
from rv.domain.models.github import (
    PR,
    FullPR,
    PRComment,
    PRConversation,
    PRLocator,
    Review,
    Thread,
    ThreadComment,
)
from rv.domain.ports import VCS, Forge, Store


@fixture
def store():
    return create_autospec(Store)


@fixture
def vcs():
    vcs = create_autospec(VCS)
    vcs.get_current_branch.return_value = "feat/sth"
    vcs.get_origin.return_value = "git@github.com/owner/repo"
    return vcs


@fixture
def forge(sample_repo):
    forge = create_autospec(Forge)
    forge.parse_repo.return_value = sample_repo
    return forge


@fixture
def ui():
    return create_autospec(ListConvoUI)


@fixture
def action(store, forge, vcs, ui):
    return ListConvo(store=store, forge=forge, vcs=vcs, ui=ui)


@fixture
def unresolved_thread():
    return Thread(
        id="1",
        is_resolved=False,
        path="src/main.py",
        line=10,
        commit_sha="abc",
        review_id="4",
        comments=[
            ThreadComment(
                id="11",
                body="Fix this",
                author="alice",
                created_at=datetime.fromisoformat("2024-01-01T10:00:00+00:00"),
            ),
        ],
    )


@fixture
def resolved_thread():
    return Thread(
        id="2",
        is_resolved=True,
        path="src/lib.py",
        line=42,
        commit_sha="def",
        review_id="4",
        comments=[
            ThreadComment(
                id="21",
                body="Done",
                author="bob",
                created_at=datetime.fromisoformat("2024-01-02T10:00:00+00:00"),
            ),
        ],
    )


@fixture
def sample_pr_comment():
    return PRComment(
        id="3",
        author="carol",
        body="General comment",
        created_at=datetime.fromisoformat("2024-01-03T10:00:00+00:00"),
    )


@fixture
def sample_review():
    return Review(
        id="4",
        author="dave",
        body="Looks good",
        created_at=datetime.fromisoformat("2024-01-04T10:00:00+00:00"),
        state="approved",
        commit="abc123",
    )


@fixture
def empty_review():
    return Review(
        id="4",
        author="dave",
        body="",
        created_at=datetime.fromisoformat("2024-01-04T10:00:00+00:00"),
        state="approved",
        commit="abc123",
    )


@fixture
def deep_thread():
    return Thread(
        id="5",
        is_resolved=False,
        path="src/rv/domain/ports.py",
        line=1,
        commit_sha="ghi",
        review_id=None,
        comments=[
            ThreadComment(
                id="51",
                body="Fix this too",
                author="alice",
                created_at=datetime.fromisoformat("2024-01-05T10:00:00+00:00"),
            ),
        ],
    )


@fixture
def full_pr_with_varied_paths(
    sample_pr: PR,
    deep_thread: Thread,
    unresolved_thread: Thread,
    sample_pr_comment: PRComment,
    sample_review: Review,
):
    return FullPR(
        pr=sample_pr,
        convo=PRConversation(
            threads=[deep_thread, unresolved_thread],
            pr_comments=[sample_pr_comment],
            reviews=[sample_review],
        ),
    )


@fixture
def full_pr_with_mixed_convo(
    sample_pr: PR,
    unresolved_thread: Thread,
    resolved_thread: Thread,
    sample_pr_comment: PRComment,
    sample_review: Review,
):
    return FullPR(
        pr=sample_pr,
        convo=PRConversation(
            threads=[unresolved_thread, resolved_thread],
            pr_comments=[sample_pr_comment],
            reviews=[sample_review],
        ),
    )


@fixture
def full_pr_with_empty_body_review(
    sample_pr: PR,
    unresolved_thread: Thread,
    resolved_thread: Thread,
    empty_review: Review,
):
    """
    Use case: the reviewer posts inline comment threads but doesn't write any PR-level comment. This happens often, and we should present it decently.
    """
    return FullPR(
        pr=sample_pr,
        convo=PRConversation(
            threads=[unresolved_thread, resolved_thread],
            pr_comments=[],
            reviews=[empty_review],
        ),
    )


class TestListConvo:
    class TestErrors:
        @staticmethod
        async def test_no_cached_pr(
            store,
            sample_pr_locator: PRLocator,
            action,
        ):
            store.get_pr.return_value = None

            opts = ListConvoOpts(pr=sample_pr_locator)

            with raises(PRNotCachedError):
                await action.exec(opts=opts)

    class TestDefaultFilter:
        @staticmethod
        async def test_unresolved_only(
            store,
            action: ListConvo,
            full_pr_with_mixed_convo: FullPR,
            ui,
        ):
            store.get_pr.return_value = full_pr_with_mixed_convo

            opts = ListConvoOpts(pr=full_pr_with_mixed_convo.pr.locator)
            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 1
            assert entries[0].id == "1"
            assert isinstance(entries[0].summary, ThreadSummary)
            assert entries[0].summary.is_resolved is False

    class TestFileFilter:
        @staticmethod
        async def test_filters_threads_by_path(
            store,
            action: ListConvo,
            full_pr_with_mixed_convo: FullPR,
            ui,
        ):
            store.get_pr.return_value = full_pr_with_mixed_convo

            opts = ListConvoOpts(
                pr=full_pr_with_mixed_convo.pr.locator,
                all=True,
                file=Path("src/lib.py"),
            )
            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 1
            assert entries[0].location == "src/lib.py:42"

        @staticmethod
        async def test_no_match(
            store,
            action: ListConvo,
            full_pr_with_mixed_convo: FullPR,
            ui,
        ):
            store.get_pr.return_value = full_pr_with_mixed_convo

            opts = ListConvoOpts(
                pr=full_pr_with_mixed_convo.pr.locator,
                all=True,
                file=Path("nonexistent.py"),
            )
            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 0

        @staticmethod
        async def test_file_with_default_filter(
            store,
            action: ListConvo,
            full_pr_with_mixed_convo: FullPR,
            ui,
        ):
            store.get_pr.return_value = full_pr_with_mixed_convo

            opts = ListConvoOpts(
                pr=full_pr_with_mixed_convo.pr.locator,
                file=Path("src/main.py"),
            )
            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 1
            assert entries[0].location == "src/main.py:10"

        @staticmethod
        async def test_filters_by_directory(
            store,
            action: ListConvo,
            full_pr_with_varied_paths: FullPR,
            ui,
        ):
            store.get_pr.return_value = full_pr_with_varied_paths

            opts = ListConvoOpts(
                pr=full_pr_with_varied_paths.pr.locator,
                all=True,
                file=Path("src/rv"),
            )
            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 1
            assert entries[0].location == "src/rv/domain/ports.py:1"

        @staticmethod
        async def test_directory_no_match(
            store,
            action: ListConvo,
            full_pr_with_varied_paths: FullPR,
            ui,
        ):
            store.get_pr.return_value = full_pr_with_varied_paths

            opts = ListConvoOpts(
                pr=full_pr_with_varied_paths.pr.locator,
                all=True,
                file=Path("src/other"),
            )
            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 0

    class TestPRCommentFilter:
        @staticmethod
        async def test_empty_review_with_threads(
            store,
            action: ListConvo,
            full_pr_with_empty_body_review: FullPR,
            ui,
        ):
            full_pr = full_pr_with_empty_body_review
            store.get_pr.return_value = full_pr
            opts = ListConvoOpts(
                pr=full_pr.pr.locator,
                reviews=True,
                pr_comments=False,
                resolved=False,
                unresolved=False,
            )

            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 1

            entry = entries[0]
            assert entry.type == "review"
            assert isinstance(entry.summary, ReviewSummary)
            assert entry.summary.n_posted_threads == 2
            assert entry.summary.state == "approved"

    class TestAllFilter:
        @staticmethod
        async def test_shows_all_types(
            store,
            action: ListConvo,
            full_pr_with_mixed_convo: FullPR,
            ui,
        ):
            store.get_pr.return_value = full_pr_with_mixed_convo

            opts = ListConvoOpts(pr=full_pr_with_mixed_convo.pr.locator, all=True)
            await action.exec(opts=opts)

            ui.show_list.assert_called_once()
            entries: list[ListEntry] = ui.show_list.call_args.args[0]
            assert len(entries) == 4
            ids = {e.id for e in entries}
            assert ids == {"1", "2", "3", "4"}
