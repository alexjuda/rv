import click
import importlib.metadata
import os
import subprocess
from datetime import datetime, timezone
from dataclasses import dataclass
from tabulate import tabulate

from rv.config import load_config
from rv.cache import CacheStore
from rv.git import (
    get_current_branch,
    get_current_commit,
    is_git_repo,
    NotAGitRepoError,
    DetachedHeadError,
    get_remote_origin,
    parse_github_remote,
)
from rv.github import create_provider
from rv.auth import login as auth_login, logout as auth_logout, auth_status
from rv.models import Meta, PR, State
from rv.lsp import main as lsp_main


@dataclass
class RepoContext:
    owner: str
    repo: str
    pr_number: int
    pr: PR


@dataclass
class ThreadDivergence:
    deleted: bool = False
    resolved_by: str | None = None
    new_comments: int = 0
    has_changes: bool = False


def _check_thread_divergence(
    owner: str, repo: str, pr_number: int, thread_id: str, cache: CacheStore
) -> ThreadDivergence | None:
    """Check if remote thread differs from local cache.

    Returns None if no divergence, or a ThreadDivergence describing the changes.
    """
    provider = create_provider()
    remote_thread = provider.get_thread(owner, repo, pr_number, thread_id)

    if remote_thread is None:
        return ThreadDivergence(deleted=True)

    local_thread = cache.read_thread(owner, repo, pr_number, thread_id)

    if local_thread is None:
        return ThreadDivergence(new_comments=len(remote_thread.comments))

    divergence = ThreadDivergence()

    if remote_thread.resolved and not local_thread.resolved:
        divergence = ThreadDivergence(
            resolved_by=remote_thread.comments[-1].author
            if remote_thread.comments
            else None
        )

    remote_comment_ids = {c.id for c in remote_thread.comments}
    local_comment_ids = {c.id for c in local_thread.comments}
    new_comment_count = len(remote_comment_ids - local_comment_ids)

    if new_comment_count > 0:
        divergence = ThreadDivergence(
            deleted=divergence.deleted,
            resolved_by=divergence.resolved_by,
            new_comments=new_comment_count,
            has_changes=True,
        )

    return divergence if divergence.has_changes else None


def _get_cache() -> CacheStore:
    ctx = click.get_current_context()
    injected = ctx.ensure_object(dict).get("cache")
    return injected if injected is not None else CacheStore()


def check_head_mismatch(owner: str, repo: str, pr_number: int) -> None:
    """Check if HEAD differs from cached commit and warn user."""
    cache = CacheStore()
    meta = cache.read_meta(owner, repo, pr_number)
    if meta is None:
        return

    if meta.synced_at_commit is None:
        return

    try:
        current_commit = get_current_commit()
    except (NotAGitRepoError, DetachedHeadError):
        return

    if current_commit != meta.synced_at_commit:
        click.echo(
            f"Warning: cache synced at {meta.synced_at_commit[:7]}, "
            f"HEAD is now {current_commit[:7]} — line numbers may be off; "
            f"run `rv pull`",
            err=True,
        )


def _run_pull() -> None:
    """Run the pull command programmatically."""
    try:
        if not is_git_repo():
            return

        branch = get_current_branch()
    except (NotAGitRepoError, DetachedHeadError):
        return

    remote = get_remote_origin()
    if not remote:
        return

    parsed = parse_github_remote(remote)
    if not parsed:
        return

    owner, repo = parsed
    _do_pull(owner, repo, branch)


def ensure_fresh_cache(owner: str, repo: str, pr_number: int) -> bool:
    """Check if cache is stale and auto-pull if needed.

    Returns True if pull was executed, False otherwise.
    """
    cache = CacheStore()
    meta = cache.read_meta(owner, repo, pr_number)
    if meta is None:
        return False

    config = load_config()
    if cache.is_stale(owner, repo, pr_number, config.stale_threshold_minutes):
        _run_pull()
        return True
    return False


def _resolve_repo(require_cache: bool = True) -> RepoContext:
    """Resolve owner, repo, and PR number from current git state.

    Args:
        require_cache: If True, require cached PR data; if False, fetch from API if needed.

    Returns:
        RepoContext with owner, repo, pr_number, and pr.

    Raises:
        SystemExit(1) on errors.
    """
    ctx = click.get_current_context()
    obj = ctx.ensure_object(dict)
    injected = obj.get("repo_context")
    if injected is not None:
        return injected

    try:
        if not is_git_repo():
            click.echo("Error: not a git repository", err=True)
            raise SystemExit(1)

        branch = get_current_branch()
    except NotAGitRepoError:
        click.echo("Error: not a git repository", err=True)
        raise SystemExit(1)
    except DetachedHeadError:
        click.echo("Error: cannot determine branch (detached HEAD)", err=True)
        raise SystemExit(1)

    remote = get_remote_origin()
    if not remote:
        click.echo("Error: no remote origin found", err=True)
        raise SystemExit(1)

    parsed = parse_github_remote(remote)
    if not parsed:
        click.echo("Error: could not parse GitHub remote", err=True)
        raise SystemExit(1)

    owner, repo = parsed
    cache = _get_cache()

    pr_number = _find_pr_number(owner, repo, branch, cache, require_cache)
    if pr_number is None:
        if require_cache:
            click.echo("Error: no cached PR — run `rv pull` first", err=True)
            raise SystemExit(1)
        try:
            provider = create_provider()
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo("Run `rv auth login` or set GITHUB_TOKEN", err=True)
            raise SystemExit(1)

        pr = provider.get_pr_for_branch(owner, repo, branch)
        if not pr:
            click.echo(f"Error: no open PR found for branch `{branch}`", err=True)
            raise SystemExit(1)
        return RepoContext(owner, repo, pr.number, pr)

    meta = cache.read_meta(owner, repo, pr_number)
    if meta is None:
        click.echo("Error: no cached PR — run `rv pull` first", err=True)
        raise SystemExit(1)

    return RepoContext(owner, repo, pr_number, meta.pr)


def _find_pr_number(
    owner: str, repo: str, branch: str, cache: CacheStore, require_cache: bool
) -> int | None:
    """Find PR number for current branch from cache or state."""
    cache_root = cache._cache_root / owner / repo
    if not cache_root.exists():
        return None

    for pr_dir in cache_root.iterdir():
        if not pr_dir.is_dir():
            continue
        try:
            pr_number = int(pr_dir.name)
        except ValueError:
            continue

        meta = cache.read_meta(owner, repo, pr_number)
        if meta and meta.pr.head_branch == branch:
            return pr_number

    return None


def _read_version():
    return importlib.metadata.version("rv")


def _do_pull(owner: str, repo: str, branch: str) -> None:
    try:
        provider = create_provider()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Run `rv auth login` or set GITHUB_TOKEN", err=True)
        raise SystemExit(1)

    pr = provider.get_pr_for_branch(owner, repo, branch)
    if not pr:
        click.echo(f"Error: no open PR found for branch `{branch}`", err=True)
        raise SystemExit(1)

    threads = provider.get_threads(owner, repo, pr.number)

    meta = Meta(
        rv_version=_read_version(),
        synced_at=datetime.now(timezone.utc).isoformat(),
        synced_at_commit=get_current_commit(),
        pr=pr,
    )
    cache = _get_cache()
    cache.write_meta(owner, repo, pr.number, meta)

    for thread in threads:
        cache.write_thread(owner, repo, pr.number, thread)

    state = cache.read_state(owner, repo, pr.number)
    if state is None:
        cache.write_state(owner, repo, pr.number, State(current_thread_id=None))

    click.echo(f"Pulled {len(threads)} threads for PR #{pr.number}")


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
def cli(ctx):
    """Code review tool for the terminal."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        ctx.invoke(status)


@cli.command()
def pull():
    """Fetch current branch's PR from GitHub into cache."""
    try:
        if not is_git_repo():
            click.echo("Error: not a git repository", err=True)
            raise SystemExit(1)

        branch = get_current_branch()
    except NotAGitRepoError:
        click.echo("Error: not a git repository", err=True)
        raise SystemExit(1)
    except DetachedHeadError:
        click.echo("Error: cannot determine branch (detached HEAD)", err=True)
        raise SystemExit(1)

    remote = get_remote_origin()
    if not remote:
        click.echo("Error: no remote origin found", err=True)
        raise SystemExit(1)

    parsed = parse_github_remote(remote)
    if not parsed:
        click.echo("Error: could not parse GitHub remote", err=True)
        raise SystemExit(1)

    owner, repo = parsed

    try:
        create_provider()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Run `rv auth login` or set GITHUB_TOKEN", err=True)
        raise SystemExit(1)

    _do_pull(owner, repo, branch)


@cli.command()
def status():
    """Show PR summary: title, URL, branches, thread counts."""
    ctx = _resolve_repo(require_cache=False)

    cache = _get_cache()
    check_head_mismatch(ctx.owner, ctx.repo, ctx.pr_number)
    threads = cache.list_threads(ctx.owner, ctx.repo, ctx.pr_number)
    open_count = sum(1 for t in threads if not t.resolved)
    resolved_count = sum(1 for t in threads if t.resolved)

    click.echo(f"PR #{ctx.pr.number}: {ctx.pr.title}")
    click.echo(f"URL: {ctx.pr.url}")
    click.echo(f"Branches: {ctx.pr.base_branch} <- {ctx.pr.head_branch}")

    meta = cache.read_meta(ctx.owner, ctx.repo, ctx.pr_number)
    if meta:
        click.echo(f"Last synced: {meta.synced_at}")

    click.echo(
        f"Threads: {open_count} open / {resolved_count} resolved / {len(threads)} total"
    )

    state = cache.read_state(ctx.owner, ctx.repo, ctx.pr_number)
    if state and state.current_thread_id:
        current = cache.read_thread(
            ctx.owner, ctx.repo, ctx.pr_number, state.current_thread_id
        )
        if current:
            first_comment = current.comments[0].body if current.comments else ""
            first_line = first_comment.split("\n")[0][:60]
            click.echo(f"Current thread: {current.file}:{current.line} — {first_line}")


@cli.command()
def list():
    """List threads: thread-id, file:line, author, first line, resolved?"""
    ctx = _resolve_repo()

    cache = _get_cache()
    check_head_mismatch(ctx.owner, ctx.repo, ctx.pr_number)
    threads = cache.list_threads(ctx.owner, ctx.repo, ctx.pr_number)

    state = cache.read_state(ctx.owner, ctx.repo, ctx.pr_number)
    current_id = state.current_thread_id if state else None

    rows = []
    for thread in threads:
        thread_id = f"> {thread.id}" if thread.id == current_id else thread.id
        first_line = thread.comments[0].body.split("\n")[0] if thread.comments else ""
        resolved = "Yes" if thread.resolved else "No"
        if thread.outdated:
            resolved += " [OUTDATED]"
        rows.append(
            [
                thread_id,
                f"{thread.file}:{thread.line}",
                thread.comments[0].author if thread.comments else "",
                first_line,
                resolved,
            ]
        )

    headers = ["Thread ID", "File:Line", "Author", "First Line", "Resolved"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))


@cli.command()
def next():
    """Advance to next unresolved thread and open editor."""
    ctx = _resolve_repo()

    cache = _get_cache()
    check_head_mismatch(ctx.owner, ctx.repo, ctx.pr_number)
    threads = cache.list_threads(ctx.owner, ctx.repo, ctx.pr_number)
    unresolved = sorted(
        [t for t in threads if not t.resolved], key=lambda t: (t.file, t.line)
    )

    if not unresolved:
        click.echo("No unresolved threads")
        return

    state = cache.read_state(ctx.owner, ctx.repo, ctx.pr_number)
    current_id = state.current_thread_id if state else None

    current_index = -1
    if current_id is not None:
        for i, t in enumerate(unresolved):
            if t.id == current_id:
                current_index = i
                break

    next_index = (current_index + 1) % len(unresolved)
    next_thread = unresolved[next_index]

    if next_thread is None:
        click.echo("No unresolved threads")
        return

    cache.write_state(
        ctx.owner,
        ctx.repo,
        ctx.pr_number,
        State(current_thread_id=next_thread.id),
    )

    click.echo(f"Thread: {next_thread.file}:{next_thread.line}")
    for comment in next_thread.comments:
        click.echo(f"@{comment.author}: {comment.body}")

    if click.confirm(
        f"Open $EDITOR at {next_thread.file}:{next_thread.line}?", default=True
    ):
        editor = os.getenv("EDITOR", "vim")
        subprocess.run([editor, f"+{next_thread.line}", next_thread.file], check=False)


@cli.command()
@click.argument("thread_id", required=False)
def show(thread_id):
    """Show thread content (defaults to current thread)."""
    ctx = _resolve_repo()

    cache = _get_cache()
    check_head_mismatch(ctx.owner, ctx.repo, ctx.pr_number)

    if thread_id is None:
        state = cache.read_state(ctx.owner, ctx.repo, ctx.pr_number)
        if state is None or state.current_thread_id is None:
            click.echo("Error: no current thread — run `rv next` first", err=True)
            raise SystemExit(1)
        thread_id = state.current_thread_id

    thread = cache.read_thread(ctx.owner, ctx.repo, ctx.pr_number, thread_id)
    if thread is None:
        click.echo(f"Error: thread {thread_id} not found", err=True)
        raise SystemExit(1)

    click.echo(f"Thread: {thread.id}")
    click.echo(f"File: {thread.file}:{thread.line}")
    if thread.outdated:
        click.echo("[OUTDATED]")
    if thread.resolved:
        click.echo("[RESOLVED]")
    click.echo()
    for comment in thread.comments:
        click.echo(f"@{comment.author} at {comment.created_at}:")
        click.echo(f"  {comment.body}")


@cli.command()
@click.argument("thread_id", required=False)
def edit(thread_id):
    """Open $EDITOR at the thread location (without advancing cursor)."""
    ctx = _resolve_repo()

    cache = _get_cache()
    check_head_mismatch(ctx.owner, ctx.repo, ctx.pr_number)

    if thread_id is None:
        state = cache.read_state(ctx.owner, ctx.repo, ctx.pr_number)
        if state is None or state.current_thread_id is None:
            click.echo("Error: no current thread — run `rv next` first", err=True)
            raise SystemExit(1)
        thread_id = state.current_thread_id
    else:
        cache.write_state(
            ctx.owner, ctx.repo, ctx.pr_number, State(current_thread_id=thread_id)
        )

    thread = cache.read_thread(ctx.owner, ctx.repo, ctx.pr_number, thread_id)
    if thread is None:
        click.echo(f"Error: thread {thread_id} not found", err=True)
        raise SystemExit(1)

    editor_bin = os.getenv("EDITOR", "vim")
    click.echo(f"Opening {editor_bin} at {thread.file}:{thread.line}...")
    subprocess.run([editor_bin, f"+{thread.line}", thread.file])


@cli.command()
@click.argument("thread_id", required=False)
@click.option("-m", "--message", help="Reply message")
@click.option("-e", "--editor", is_flag=True, help="Open editor to compose")
@click.option("--canned", help="Use canned reply from config")
def reply(thread_id, message, editor, canned):
    """Post a reply to a thread."""
    ctx = _resolve_repo()

    cache = _get_cache()
    check_head_mismatch(ctx.owner, ctx.repo, ctx.pr_number)

    if thread_id is None:
        state = cache.read_state(ctx.owner, ctx.repo, ctx.pr_number)
        if state is None or state.current_thread_id is None:
            click.echo("Error: no current thread — run `rv next` first", err=True)
            raise SystemExit(1)
        thread_id = state.current_thread_id
    else:
        cache.write_state(
            ctx.owner, ctx.repo, ctx.pr_number, State(current_thread_id=thread_id)
        )

    if editor:
        editor_bin = os.getenv("EDITOR", "vim")
        click.echo("Opening editor... (write message and save)")
        subprocess.run([editor_bin], check=False)
        message = click.prompt("Enter your reply")
    elif canned:
        config = load_config()
        message = config.canned_replies.get(canned, f"{{{canned}}}")
    elif message is None:
        message = click.prompt("Enter your reply")

    divergence = _check_thread_divergence(
        ctx.owner, ctx.repo, ctx.pr_number, thread_id, cache
    )

    if divergence and divergence.deleted:
        click.echo("Error: thread no longer exists on GitHub", err=True)
        raise SystemExit(1)

    if divergence and divergence.resolved_by:
        if message:
            click.echo(
                f"Warning: thread was resolved by {divergence.resolved_by} — posting anyway"
            )
        else:
            click.echo(
                f"Error: thread was resolved by {divergence.resolved_by}", err=True
            )
            raise SystemExit(1)

    if divergence and divergence.new_comments > 0:
        if message:
            click.echo(
                f"Warning: {divergence.new_comments} new comment(s) on this thread — posting anyway"
            )
        else:
            click.echo(
                f"Error: new activity on this thread ({divergence.new_comments} new comment(s))",
                err=True,
            )
            raise SystemExit(1)

    try:
        provider = create_provider()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    try:
        provider.post_reply(ctx.owner, ctx.repo, ctx.pr_number, thread_id, message)
        click.echo("Reply posted")
    except Exception as e:
        click.echo(f"Error posting reply: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("thread_id", required=False)
@click.option("-m", "--message", help="Reply message")
@click.option("-e", "--editor", is_flag=True, help="Open editor to compose")
@click.option("--canned", help="Use canned reply from config")
def resolve(thread_id, message, editor, canned):
    """Mark thread resolved (optionally with a reply)."""
    ctx = _resolve_repo()

    cache = _get_cache()
    check_head_mismatch(ctx.owner, ctx.repo, ctx.pr_number)

    if thread_id is None:
        state = cache.read_state(ctx.owner, ctx.repo, ctx.pr_number)
        if state is None or state.current_thread_id is None:
            click.echo("Error: no current thread — run `rv next` first", err=True)
            raise SystemExit(1)
        thread_id = state.current_thread_id

    body = None
    if message or editor or canned:
        if editor:
            editor_bin = os.getenv("EDITOR", "vim")
            subprocess.run([editor_bin], check=False)
            body = click.prompt("Enter your reply")
        elif canned:
            config = load_config()
            body = config.canned_replies.get(canned, f"{{{canned}}}")
        elif message:
            body = message

    divergence = _check_thread_divergence(
        ctx.owner, ctx.repo, ctx.pr_number, thread_id, cache
    )

    if divergence and divergence.deleted:
        click.echo("Error: thread no longer exists on GitHub", err=True)
        raise SystemExit(1)

    if divergence and divergence.new_comments > 0:
        click.echo(
            f"Warning: {divergence.new_comments} new comment(s) on this thread — continuing"
        )

    try:
        provider = create_provider()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    try:
        if body:
            provider.post_reply(ctx.owner, ctx.repo, ctx.pr_number, thread_id, body)
            click.echo("Reply posted")
        provider.resolve_thread(ctx.owner, ctx.repo, ctx.pr_number, thread_id)
        click.echo("Thread resolved")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
def lsp():
    """Start LSP server for diagnostics."""
    lsp_main()


@cli.group()
def auth():
    """Manage GitHub authentication."""
    pass


@auth.command()
@click.argument("token")
def login(token):
    """Login with GitHub token."""
    auth_login(token)
    click.echo("Logged in successfully")


@auth.command()
def logout():
    """Logout and remove token."""
    auth_logout()
    click.echo("Logged out")


@auth.command(name="status")
def auth_status_cmd():
    """Show auth status."""
    status = auth_status()
    if status["has_token"]:
        click.echo(f"Token source: {status['mechanism']}")
    else:
        click.echo("Not logged in")


def main():
    cli()


if __name__ == "__main__":
    main()
