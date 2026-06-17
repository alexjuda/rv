"""
Utilities to parse non-standard CLI argument formats.
"""

import re

from ..domain.models.github import PRLocator, RepoLocator


def parse_pr_ref(pr: str | None) -> int | PRLocator | None:
    if pr is None:
        return None

    if match := re.match(r"(?:([^/#]+)\/([^/#]+)#)?#?(\d+)", pr):
        assert len(match.groups()) == 3
        owner = match.group(1)
        repo = match.group(2)
        pr_num = int(match.group(3))
        if owner and repo:
            return PRLocator(RepoLocator(owner, repo), pr_num)
        else:
            return pr_num

    raise ValueError()
