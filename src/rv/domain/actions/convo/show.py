import re
from dataclasses import dataclass
from typing import Protocol

from ...models.github import PRComment, PRLocator, RepoLocator, Review, Thread
from ...ports import VCS, Forge, Store

_PR_REF_PATTERN = re.compile(r"^(?:([\w.-]+/[\w.-]+))?#(\d+)$")


@dataclass
class CodeContext:
    path: str
    commit_sha: str
    target_line: int
    start_line: int
    lines: list[str]


class ShowConvoUI(Protocol):
    def show_thread(
        self,
        thread: Thread,
        pr_loc: PRLocator | None,
        context: CodeContext | None,
    ) -> None: ...

    def show_pr_comment(self, comment: PRComment, pr_loc: PRLocator) -> None: ...

    def show_review(self, review: Review, pr_loc: PRLocator) -> None: ...

    def show_pr_conversation(
        self,
        pr_comments: list[PRComment],
        reviews: list[Review],
        pr_loc: PRLocator,
    ) -> None: ...

    def show_not_found(self, id: str) -> None: ...


class ShowConvo:
    def __init__(self, store: Store, vcs: VCS, forge: Forge, ui: ShowConvoUI):
        self._store = store
        self._vcs = vcs
        self._forge = forge
        self._ui = ui

    def exec(self, id: str, context_lines: int = 5) -> None:
        match = _PR_REF_PATTERN.match(id)
        if match:
            self._exec_pr_ref(match)
            return

        thread = self._store.get_thread(id)
        if thread is not None:
            pr_loc = self._store.get_pr_locator_for_thread(id)
            context = self._load_code_context(thread, context_lines)
            self._ui.show_thread(thread, pr_loc, context)
            return

        comment = self._store.get_pr_comment(id)
        if comment is not None:
            pr_loc = self._store.get_pr_locator_for_pr_comment(id)
            if pr_loc is None:
                self._ui.show_not_found(id)
                return
            self._ui.show_pr_comment(comment, pr_loc)
            return

        review = self._store.get_review(id)
        if review is not None:
            pr_loc = self._store.get_pr_locator_for_review(id)
            if pr_loc is None:
                self._ui.show_not_found(id)
                return
            self._ui.show_review(review, pr_loc)
            return

        self._ui.show_not_found(id)

    def _exec_pr_ref(self, match: re.Match[str]) -> None:
        repo_str, number_str = match.group(1), match.group(2)
        number = int(number_str)

        if repo_str:
            owner, repo = repo_str.split("/", 1)
            pr_loc = PRLocator(RepoLocator(owner, repo), number)
        else:
            origin = self._vcs.get_origin()
            repo = self._forge.parse_repo(origin)
            pr_loc = PRLocator(repo, number)

        full_pr = self._store.get_pr(pr_loc)
        if full_pr is None:
            self._ui.show_not_found(match.group(0))
            return

        self._ui.show_pr_conversation(
            full_pr.convo.pr_comments,
            full_pr.convo.reviews,
            pr_loc,
        )

    def _load_code_context(self, thread: Thread, n: int) -> CodeContext | None:
        content = self._vcs.read_file(thread.path, thread.commit_sha)
        if content is None:
            return None

        lines = content.splitlines()
        idx = thread.line - 1
        start = max(0, idx - n)
        end = min(len(lines), idx + n + 1)
        return CodeContext(
            path=thread.path,
            commit_sha=thread.commit_sha,
            target_line=thread.line,
            start_line=start + 1,
            lines=lines[start:end],
        )
