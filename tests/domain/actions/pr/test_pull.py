from copy import deepcopy
from unittest.mock import create_autospec

from pytest import fixture, raises

from rv.domain.actions.pull import Pull, PullUI
from rv.domain.exceptions import GitError
from rv.domain.models.github import (
    FullPR,
    PRLocator,
    RepoLocator,
)
from rv.domain.ports import VCS, Forge, Store

# --- mock fixtures ---


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
def forge(sample_repo: RepoLocator):
    forge = create_autospec(Forge)
    forge.parse_repo.return_value = sample_repo
    return forge


@fixture
def ui():
    return create_autospec(PullUI)


@fixture
def action(store, forge, vcs, ui):
    return Pull(store=store, forge=forge, vcs=vcs, ui=ui)


# --- data fixtures ---


@fixture
def empty_full_pr(sample_full_pr: FullPR):
    empty_pr = deepcopy(sample_full_pr)
    empty_pr.convo.threads = []
    return empty_pr


# --- test cases ---


class TestPull:
    # --- happy path ---
    @staticmethod
    async def test_with_full_locator(
        sample_pr_locator: RepoLocator,
        sample_full_pr: FullPR,
        forge,
        ui,
        store,
        action: Pull,
    ):
        forge.get_pr.return_value = sample_full_pr
        pr = PRLocator(sample_pr_locator, 42)

        await action.exec(pr_arg=pr)

        ui.fetching_heads_up.assert_called()

        # Store is empty by default. Only new data => no need to confirm.
        ui.confirm.assert_not_called()
        ui.ack_summary.assert_called()

        store.store_pr.assert_called_with(sample_full_pr)

    @staticmethod
    async def test_with_pr_number(
        sample_full_pr: FullPR,
        forge,
        ui,
        store,
        action: Pull,
    ):
        forge.get_pr.return_value = sample_full_pr
        pr = 42

        await action.exec(pr_arg=pr)

        # Store is empty by default. Only new data => no need to confirm.
        ui.confirm.assert_not_called()
        ui.ack_summary.assert_called()

        store.store_pr.assert_called_with(sample_full_pr)

    @staticmethod
    async def test_no_pr_number(
        sample_pr_locator: RepoLocator,
        sample_full_pr: FullPR,
        forge,
        store,
        action: Pull,
    ):
        forge.find_pr_for_branch.return_value = sample_pr_locator
        forge.get_pr.return_value = sample_full_pr

        await action.exec(pr_arg=None)

        store.store_pr.assert_called_with(sample_full_pr)

    @staticmethod
    async def test_asks_when_needed(
        sample_pr_locator: RepoLocator,
        store,
        forge,
        ui,
        action: Pull,
        sample_full_pr: FullPR,
        empty_full_pr: FullPR,
    ):
        # before: some conversations
        # after: no conversations
        # => needs confirming
        store.get_pr.return_value = sample_full_pr
        forge.get_pr.return_value = empty_full_pr
        ui.confirm.return_value = True

        pr = PRLocator(sample_pr_locator, 42)

        await action.exec(pr_arg=pr)

        ui.confirm.assert_called()

        summary = ui.confirm.call_args.args[0]

        assert summary.stat.threads.n_new == 0
        assert summary.stat.threads.n_deleted == 1
        assert summary.stat.threads.n_changed == 0

        ui.ack_confirmation.assert_called_with(saved=True)

        store.store_pr.assert_called_with(empty_full_pr)

    @staticmethod
    async def test_skipping_destructive_operation(
        sample_pr_locator: RepoLocator,
        store,
        forge,
        ui,
        action: Pull,
        sample_full_pr: FullPR,
        empty_full_pr: FullPR,
    ):
        # before: some conversations
        # after: no conversations
        # => needs confirming
        store.get_pr.return_value = sample_full_pr
        forge.get_pr.return_value = empty_full_pr
        ui.confirm.return_value = False

        pr = PRLocator(sample_pr_locator, 42)

        await action.exec(pr_arg=pr)

        ui.ack_confirmation.assert_called_with(saved=False)

        store.store_pr.assert_not_called()

    # --- errors ---

    @staticmethod
    async def test_git_error(vcs, action: Pull):
        vcs.get_origin.side_effect = GitError()

        with raises(GitError):
            await action.exec(pr_arg=None)
