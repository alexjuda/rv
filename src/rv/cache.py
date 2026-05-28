import fcntl
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rv.models import Meta, State, Thread, CachePath


def get_cache_dir() -> Path:
    data_home = os.getenv("XDG_DATA_HOME")
    if data_home is None:
        data_home = Path.home() / ".local" / "share"
    return Path(data_home) / "rv"


class CacheError(Exception):
    pass


class CacheStore:
    def __init__(self, cache_root: Path | None = None):
        self._cache_root = cache_root or get_cache_dir()

    def _get_cache_path(self, owner: str, repo: str, pr_number: int) -> CachePath:
        return CachePath(owner, repo, pr_number)

    def _ensure_dir(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        self._ensure_dir(path)
        lock_path = path.parent / f"{path.name}.lock"
        lock_path.touch()
        tmp_path = Path(f"{path}.{os.getpid()}.tmp")
        try:
            with open(lock_path, "w") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    with tmp_path.open("w") as f:
                        json.dump(data, f)
                    os.rename(tmp_path, path)
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def write_meta(self, owner: str, repo: str, pr_number: int, meta: Meta) -> None:
        cache_path = self._get_cache_path(owner, repo, pr_number)
        path = self._cache_root / cache_path.meta()
        self._atomic_write(path, meta.to_dict())

    def read_meta(self, owner: str, repo: str, pr_number: int) -> Meta | None:
        cache_path = self._get_cache_path(owner, repo, pr_number)
        path = self._cache_root / cache_path.meta()
        if not path.exists():
            return None
        try:
            with path.open() as f:
                data = json.load(f)
            return Meta.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def write_state(self, owner: str, repo: str, pr_number: int, state: State) -> None:
        cache_path = self._get_cache_path(owner, repo, pr_number)
        path = self._cache_root / cache_path.state()
        self._atomic_write(path, state.to_dict())

    def read_state(self, owner: str, repo: str, pr_number: int) -> State | None:
        cache_path = self._get_cache_path(owner, repo, pr_number)
        path = self._cache_root / cache_path.state()
        if not path.exists():
            return None
        try:
            with path.open() as f:
                data = json.load(f)
            return State.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def write_thread(
        self, owner: str, repo: str, pr_number: int, thread: Thread
    ) -> None:
        cache_path = self._get_cache_path(owner, repo, pr_number)
        path = self._cache_root / cache_path.thread_file(thread.id)
        self._atomic_write(path, thread.to_dict())

    def read_thread(
        self, owner: str, repo: str, pr_number: int, thread_id: str
    ) -> Thread | None:
        cache_path = self._get_cache_path(owner, repo, pr_number)
        path = self._cache_root / cache_path.thread_file(thread_id)
        if not path.exists():
            return None
        try:
            with path.open() as f:
                data = json.load(f)
            return Thread.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def list_threads(self, owner: str, repo: str, pr_number: int) -> list[Thread]:
        cache_path = self._get_cache_path(owner, repo, pr_number)
        threads_dir = self._cache_root / cache_path.threads_dir()
        if not threads_dir.exists():
            return []
        threads = []
        for f in threads_dir.glob("*.json"):
            try:
                with f.open() as fp:
                    data = json.load(fp)
                threads.append(Thread.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        return threads

    def is_stale(
        self, owner: str, repo: str, pr_number: int, stale_threshold_minutes: int
    ) -> bool:
        meta = self.read_meta(owner, repo, pr_number)
        if meta is None:
            return True

        try:
            synced = datetime.fromisoformat(meta.synced_at.replace("Z", "+00:00"))
        except ValueError:
            return True

        now = datetime.now(timezone.utc)
        delta = (now - synced).total_seconds() / 60
        return delta > stale_threshold_minutes
