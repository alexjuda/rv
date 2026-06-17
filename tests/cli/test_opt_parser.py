from pytest import mark, raises

from rv.cli._opt_parser import parse_pr_ref
from rv.domain.models.github import PRLocator, RepoLocator


class TestParsePRRef:
    @staticmethod
    @mark.parametrize(
        "opt,pr_loc",
        [
            ("42", 42),
            (None, None),
            ("#42", 42),
            ("owner/repo#42", PRLocator(RepoLocator("owner", "repo"), 42)),
        ],
    )
    def test_valid(opt, pr_loc):
        parsed = parse_pr_ref(opt)
        assert parsed == pr_loc

    @staticmethod
    @mark.parametrize(
        "opt",
        [
            "abc123",
            "abc",
            "repo/42",
            "owner/repo/42",
        ],
    )
    def test_invalid(opt):
        with raises(ValueError):
            _ = parse_pr_ref(opt)
