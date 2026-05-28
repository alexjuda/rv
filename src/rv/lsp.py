from threading import Thread as WatcherThread
from urllib.parse import urlparse

from pygls.server import LanguageServer
from lsprotocol import types
import watchfiles

from rv.cache import CacheStore
from rv.git import (
    get_current_branch,
    get_remote_origin,
    parse_github_remote,
    NotAGitRepoError,
    DetachedHeadError,
)
from rv.models import Thread


class RVServer(LanguageServer):
    def __init__(self):
        super().__init__(name="rv", version="0.1.0")
        self._cache = CacheStore()
        self._owner: str | None = None
        self._repo: str | None = None
        self._pr_number: int | None = None
        self._threads_by_file: dict[str, list[Thread]] = {}
        self._watcher: WatcherThread | None = None

        self._register_features()
        self._start_watcher()

    def _register_features(self):
        @self.feature("textDocument/didOpen")
        def _on_text_document_did_open(params: types.DidOpenTextDocumentParams) -> None:
            if not self._load_context():
                return

            text_doc = params.text_document
            uri = text_doc.uri
            file_path = urlparse(uri).path
            diagnostics = self._get_diagnostics(file_path)
            self.publish_diagnostics(uri, diagnostics)

        @self.feature("textDocument/hover")
        def _on_text_document_hover(params: types.HoverParams) -> types.Hover | None:
            if not self._load_context():
                return None

            uri = params.text_document.uri
            file_path = urlparse(uri).path
            line = params.position.line + 1

            threads = self._threads_by_file.get(file_path)
            if threads is None:
                return None
            for thread in threads:
                if thread.start_line <= line <= thread.line:
                    content = []
                    content.append(f"Thread: {thread.id}")
                    content.append(f"File: {thread.file}:{thread.line}")
                    if thread.resolved:
                        content.append("[RESOLVED]")
                    if thread.outdated:
                        content.append("[OUTDATED]")
                    content.append("")
                    for comment in thread.comments:
                        content.append(f"@{comment.author} at {comment.created_at}:")
                        content.append(f"  {comment.body}")
                        content.append("")

                    hover_contents = types.MarkupContent(
                        kind=types.MarkupKind.Markdown,
                        value="\n".join(content),
                    )
                    return types.Hover(contents=hover_contents)

            return None

    def _load_context(self) -> bool:
        try:
            branch = get_current_branch()
            remote = get_remote_origin()
            if not remote:
                return False
            parsed = parse_github_remote(remote)
            if not parsed:
                return False
            self._owner, self._repo = parsed

            self._pr_number = self._find_pr_number(branch)
            if self._pr_number is None:
                return False

            self._reload_threads()
            return True
        except (NotAGitRepoError, DetachedHeadError, ValueError):
            return False

    def _find_pr_number(self, branch: str) -> int | None:
        """Find PR number for current branch from cache."""
        if self._owner is None or self._repo is None:
            return None

        cache_root = self._cache._cache_root / self._owner / self._repo
        if not cache_root.exists():
            return None

        for pr_dir in cache_root.iterdir():
            if not pr_dir.is_dir():
                continue
            try:
                pr_number = int(pr_dir.name)
            except ValueError:
                continue

            meta = self._cache.read_meta(self._owner, self._repo, pr_number)
            if meta and meta.pr.head_branch == branch:
                return pr_number

        return None

    def _reload_threads(self):
        self._threads_by_file.clear()
        if self._owner is None or self._repo is None or self._pr_number is None:
            return
        threads = self._cache.list_threads(self._owner, self._repo, self._pr_number)
        for thread in threads:
            if thread.file not in self._threads_by_file:
                self._threads_by_file[thread.file] = []
            self._threads_by_file[thread.file].append(thread)

    def _get_diagnostics(self, file_path: str) -> list[types.Diagnostic]:
        threads = self._threads_by_file.get(file_path, [])
        diagnostics = []
        for thread in threads:
            if thread.outdated:
                message = f"@{thread.comments[0].author}: {thread.comments[0].body.split(chr(10))[0]}  [OUTDATED]"
            else:
                message = f"@{thread.comments[0].author}: {thread.comments[0].body.split(chr(10))[0]}"
                if len(thread.comments) > 1:
                    message += f"  [{len(thread.comments)} replies]"

            start_line = thread.start_line - 1
            end_line = thread.line
            if start_line < 0:
                start_line = 0
            if end_line <= start_line:
                end_line = start_line + 1

            diagnostic = types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=start_line, character=0),
                    end=types.Position(line=end_line, character=0),
                ),
                message=message,
                source="rv",
                code=thread.id,
                severity=types.DiagnosticSeverity(4),
            )
            diagnostics.append(diagnostic)
        return diagnostics

    def _start_watcher(self) -> None:
        """Start watching the threads directory for changes."""
        try:
            cache_dir = self._cache._cache_root

            def watch_loop():
                watch_filter = watchfiles.DefaultFilter()
                for changes in watchfiles.watch(cache_dir, watch_filter=watch_filter):
                    self._on_file_change(changes)

            self._watcher = WatcherThread(target=watch_loop, daemon=True)
            self._watcher.start()
        except OSError:
            pass

    def _on_file_change(self, changes: set) -> None:
        """Handle file change events by reloading threads."""
        if self._owner and self._repo and self._pr_number:
            self._reload_threads()
            for file_path in self._threads_by_file:
                self.publish_diagnostics(
                    f"file://{file_path}",
                    self._get_diagnostics(file_path),
                )


def main():
    server = RVServer()
    server.start_io()


if __name__ == "__main__":
    main()
