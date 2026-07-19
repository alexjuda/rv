class DomainError(Exception):
    """Base for all domain-level errors."""


class GitError(DomainError):
    """Git operation failed."""


class InvalidOriginError(DomainError):
    """Git origin is not a valid remote."""


class NoMatchingPRsError(DomainError):
    """No PR found for the current branch."""


class PRNotFoundError(DomainError):
    """Expected PR does not exist."""


class IDNotFoundError(DomainError):
    """There's no item with this ID in the local store."""


class PRNotCachedError(DomainError):
    """The PR data is not in the local cache."""
