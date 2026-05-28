import glob
import os
from pathlib import Path
from unittest.mock import patch

from rv.cache import CacheStore, get_cache_dir
from rv.models import Comment, Meta, PR, State, Thread


class TestCacheDir:
    @staticmethod
    def test_default_cache_dir(tmp_path):
        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            with patch.dict(os.environ, {}, clear=False):
                if "XDG_DATA_HOME" in os.environ:
                    del os.environ["XDG_DATA_HOME"]

            cache_dir = get_cache_dir()
            assert "rv" in str(cache_dir)

    @staticmethod
    def test_custom_xdg_data_home(tmp_path):
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path / "data")}):
            cache_dir = get_cache_dir()
            assert str(cache_dir).startswith(str(tmp_path))


class TestCacheReadWrite:
    @staticmethod
    def test_write_meta_json(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc123",
            pr=PR(
                number=123,
                title="Test PR",
                url="https://github.com/owner/repo/pull/123",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )
        cache.write_meta("owner", "repo", 123, meta)
        assert (tmp_path / "owner" / "repo" / "123" / "meta.json").exists()

    @staticmethod
    def test_read_meta_json(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc123",
            pr=PR(
                number=123,
                title="Test",
                url="http://x.com",
                base_branch="main",
                head_branch="f",
                state="open",
            ),
        )
        cache.write_meta("owner", "repo", 123, meta)
        loaded = cache.read_meta("owner", "repo", 123)
        assert loaded is not None
        assert loaded.rv_version == "0.1.0"
        assert loaded.pr.number == 123

    @staticmethod
    def test_read_meta_not_exists():
        cache = CacheStore(cache_root=Path("/nonexistent"))
        result = cache.read_meta("owner", "repo", 123)
        assert result is None

    @staticmethod
    def test_write_state(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        cache.write_state("owner", "repo", 123, State(current_thread_id="PRRT_abc"))
        assert (tmp_path / "owner" / "repo" / "123" / "state.json").exists()

    @staticmethod
    def test_read_state(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        cache.write_state("owner", "repo", 123, State(current_thread_id="PRRT_abc"))
        state = cache.read_state("owner", "repo", 123)
        assert state is not None
        assert state.current_thread_id == "PRRT_abc"

    @staticmethod
    def test_read_state_not_exists():
        cache = CacheStore(cache_root=Path("/nonexistent"))
        result = cache.read_state("owner", "repo", 123)
        assert result is None

    @staticmethod
    def test_write_thread(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        thread = Thread(
            id="PRRT_abc",
            file="src/foo.py",
            line=42,
            start_line=40,
            resolved=False,
            outdated=False,
            comments=[
                Comment(
                    id="PRRC_xyz",
                    body="Comment",
                    author="reviewer",
                    created_at="2026-05-12T09:00:00Z",
                )
            ],
        )
        cache.write_thread("owner", "repo", 123, thread)
        assert (
            tmp_path / "owner" / "repo" / "123" / "threads" / "PRRT_abc.json"
        ).exists()

    @staticmethod
    def test_read_thread(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        thread = Thread(
            id="PRRT_abc",
            file="src/foo.py",
            line=42,
            start_line=40,
            resolved=False,
            outdated=False,
            comments=[
                Comment(
                    id="PRRC_xyz",
                    body="Comment",
                    author="reviewer",
                    created_at="2026-05-12T09:00:00Z",
                )
            ],
        )
        cache.write_thread("owner", "repo", 123, thread)
        loaded = cache.read_thread("owner", "repo", 123, "PRRT_abc")
        assert loaded is not None
        assert loaded.id == "PRRT_abc"

    @staticmethod
    def test_list_threads(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        for i, tid in enumerate(["PRRT_1", "PRRT_2", "PRRT_3"]):
            thread = Thread(
                id=tid,
                file=f"src/file{i}.py",
                line=10 + i,
                start_line=10,
                resolved=False,
                outdated=False,
                comments=[
                    Comment(
                        id=f"PRRC_{i}",
                        body="Comment",
                        author="reviewer",
                        created_at="2026-05-12T09:00:00Z",
                    )
                ],
            )
            cache.write_thread("owner", "repo", 123, thread)

        threads = cache.list_threads("owner", "repo", 123)
        assert len(threads) == 3


class TestStaleCheck:
    @staticmethod
    def test_is_stale_true(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        stale_threshold = 1

        meta_path = tmp_path / "owner" / "repo" / "123" / "meta.json"
        meta_path.parent.mkdir(parents=True)
        meta_path.write_text(
            '{"rv_version": "0.1.0", "synced_at": "2020-01-01T00:00:00Z", "synced_at_commit": "abc", "pr": {"number": 123, "title": "Test", "url": "http://x.com", "base_branch": "main", "head_branch": "feature", "state": "open"}}'
        )

        is_stale = cache.is_stale("owner", "repo", 123, stale_threshold)
        assert is_stale is True

    @staticmethod
    def test_is_stale_false_recent(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        stale_threshold = 500000

        meta_path = tmp_path / "owner" / "repo" / "123" / "meta.json"
        meta_path.parent.mkdir(parents=True)
        meta_path.write_text(
            '{"rv_version": "0.1.0", "synced_at": "2026-05-13T10:00:00Z", "synced_at_commit": "abc", "pr": {"number": 123, "title": "Test", "url": "http://x.com", "base_branch": "main", "head_branch": "feature", "state": "open"}}'
        )

        is_stale = cache.is_stale("owner", "repo", 123, stale_threshold)
        assert is_stale is False


class TestCacheSafety:
    @staticmethod
    def test_atomic_write_uses_temp_file(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc123",
            pr=PR(
                number=123,
                title="Test PR",
                url="https://github.com/owner/repo/pull/123",
                base_branch="main",
                head_branch="feature",
                state="open",
            ),
        )
        cache.write_meta("owner", "repo", 123, meta)
        final_path = tmp_path / "owner" / "repo" / "123" / "meta.json"
        assert final_path.exists()

        tmp_files = glob.glob(str(tmp_path / "owner" / "repo" / "123" / "*.tmp"))
        assert len(tmp_files) == 0, "No temp files should remain after write"

    @staticmethod
    def test_json_corrupted_on_read_returns_none(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        cache._atomic_write(
            tmp_path / "owner" / "repo" / "123" / "meta.json",
            {"rv_version": "0.1.0"},
        )
        result = cache.read_meta("owner", "repo", 123)
        assert result is None, (
            "Corrupted JSON (missing required fields) should return None"
        )

    @staticmethod
    def test_lock_file_created_during_write(tmp_path):
        cache = CacheStore(cache_root=tmp_path)
        cache._atomic_write(tmp_path / "subdir" / "test.json", {"key": "value"})

        lock_files = list(tmp_path.glob("**/*.lock"))
        assert len(lock_files) > 0, "Lock file should be created during write"
