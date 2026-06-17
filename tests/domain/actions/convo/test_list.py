from datetime import datetime
from unittest.mock import create_autospec

from pytest import fixture, raises

from rv.domain.actions.convo.list import ListConvo, ListConvoOpts, ListConvoUI
from rv.domain.exceptions import PRNotCachedError
from rv.domain.models.convo import ListEntry
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
        created_at="2024-01-03T10:00:00Z",
    )


@fixture
def sample_review():
    return Review(
        id="4",
        author="dave",
        body="Looks good",
        created_at="2024-01-04T10:00:00Z",
        state="approved",
        commit="abc123",
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
            assert entries[0].state == "unresolved"

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
