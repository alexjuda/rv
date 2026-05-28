import re
import subprocess


class GitError(Exception):
    pass


class NotAGitRepoError(GitError):
    pass


class DetachedHeadError(GitError):
    pass


def _run_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def is_git_repo() -> bool:
    result = _run_git("rev-parse", "--git-dir")
    return result.returncode == 0


def get_current_branch() -> str:
    result = _run_git("rev-parse", "--abbrev-ref", "HEAD")

    if result.returncode != 0:
        if "not a git repository" in result.stderr.lower():
            raise NotAGitRepoError("not a git repository")
        raise GitError(f"failed to get branch: {result.stderr}")

    branch = result.stdout.strip()

    branch_lower = branch.lower()
    if "head detached" in branch_lower or "(detached" in branch_lower:
        raise DetachedHeadError("cannot determine branch (detached HEAD)")

    if not branch:
        raise GitError("cannot determine branch")

    return branch


def get_current_commit() -> str:
    result = _run_git("rev-parse", "HEAD")

    if result.returncode != 0:
        raise GitError(f"failed to get current commit: {result.stderr}")

    return result.stdout.strip()


def get_remote_origin() -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def parse_github_remote(url: str) -> tuple[str, str] | None:
    patterns = [
        r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$",
        r"github\.com/([^/]+)/([^/.]+)(?:\.git)?$",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2)

    return None
