from dataclasses import dataclass, field
from typing import Any, Literal

__all__ = [
    "Comment",
    "Thread",
    "PR",
    "PRState",
    "Meta",
    "State",
    "ThreadFile",
    "CachePath",
    "RV_VERSION",
]

RV_VERSION = "0.1.0"


@dataclass
class Comment:
    id: str
    body: str
    author: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "body": self.body,
            "author": self.author,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Comment":
        return cls(
            id=data["id"],
            body=data["body"],
            author=data["author"],
            created_at=data["created_at"],
        )


@dataclass
class Thread:
    id: str
    file: str
    line: int
    start_line: int
    resolved: bool
    outdated: bool
    comments: list[Comment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "file": self.file,
            "line": self.line,
            "start_line": self.start_line,
            "resolved": self.resolved,
            "outdated": self.outdated,
            "comments": [c.to_dict() for c in self.comments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Thread":
        comments = [Comment.from_dict(c) for c in data.get("comments") or []]
        return cls(
            id=data["id"],
            file=data["file"],
            line=data["line"],
            start_line=data["start_line"],
            resolved=data["resolved"],
            outdated=data["outdated"],
            comments=comments,
        )


PRState = Literal["open", "closed", "merged"]


@dataclass
class PR:
    number: int
    title: str
    url: str
    base_branch: str
    head_branch: str
    state: PRState

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "base_branch": self.base_branch,
            "head_branch": self.head_branch,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PR":
        return cls(
            number=data["number"],
            title=data["title"],
            url=data["url"],
            base_branch=data["base_branch"],
            head_branch=data["head_branch"],
            state=data["state"],
        )


@dataclass
class Meta:
    rv_version: str
    synced_at: str
    synced_at_commit: str
    pr: PR

    def to_dict(self) -> dict[str, Any]:
        return {
            "rv_version": self.rv_version,
            "synced_at": self.synced_at,
            "synced_at_commit": self.synced_at_commit,
            "pr": self.pr.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Meta":
        return cls(
            rv_version=data["rv_version"],
            synced_at=data["synced_at"],
            synced_at_commit=data["synced_at_commit"],
            pr=PR.from_dict(data["pr"]),
        )


@dataclass
class State:
    current_thread_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"current_thread_id": self.current_thread_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "State":
        return cls(current_thread_id=data.get("current_thread_id"))


class ThreadFile:
    def __init__(
        self, owner: str, repo: str, pr_number: int, thread_id: str | None = None
    ):
        self.owner = owner
        self.repo = repo
        self.pr_number = pr_number
        self.thread_id = thread_id

    @property
    def directory(self) -> str:
        return f"{self.owner}/{self.repo}/{self.pr_number}/threads"

    def __str__(self) -> str:
        if self.thread_id is None:
            raise ValueError("thread_id not set")
        return f"{self.directory}/{self.thread_id}.json"


class CachePath:
    def __init__(self, owner: str, repo: str, pr_number: int):
        self.owner = owner
        self.repo = repo
        self.pr_number = pr_number

    def meta(self) -> str:
        return f"{self.owner}/{self.repo}/{self.pr_number}/meta.json"

    def state(self) -> str:
        return f"{self.owner}/{self.repo}/{self.pr_number}/state.json"

    def thread_file(self, thread_id: str) -> str:
        return f"{self.owner}/{self.repo}/{self.pr_number}/threads/{thread_id}.json"

    def threads_dir(self) -> str:
        return f"{self.owner}/{self.repo}/{self.pr_number}/threads"
