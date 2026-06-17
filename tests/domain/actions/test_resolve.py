from unittest.mock import create_autospec

from pytest import fixture, raises

from rv.domain.actions._resolve import resolve_pr_loc
from rv.domain.exceptions import NoMatchingPRsError
from rv.domain.models.github import PRLocator
from rv.domain.ports import VCS, Forge


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


class TestResolvePRLoc:
    @staticmethod
    async def test_returns_pr_locator_as_is(vcs, forge, sample_pr_locator):
        result = await resolve_pr_loc(sample_pr_locator, vcs=vcs, forge=forge)
        assert result == sample_pr_locator

    @staticmethod
    async def test_resolves_int(vcs, forge, sample_repo):
        result = await resolve_pr_loc(42, vcs=vcs, forge=forge)
        assert result == PRLocator(repo=sample_repo, number=42)

    @staticmethod
    async def test_resolves_none_to_branch(vcs, forge, sample_repo):
        expected = PRLocator(repo=sample_repo, number=7)
        forge.find_pr_for_branch.return_value = expected
        result = await resolve_pr_loc(None, vcs=vcs, forge=forge)
        assert result == expected

    @staticmethod
    async def test_raises_when_no_matching_branch(vcs, forge, sample_repo):
        forge.find_pr_for_branch.return_value = None
        with raises(NoMatchingPRsError):
            await resolve_pr_loc(None, vcs=vcs, forge=forge)
