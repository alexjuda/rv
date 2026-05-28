from dataclasses import asdict
from rv.models import (
    PR,
    Comment,
    Thread,
    Meta,
    State,
    ThreadFile,
)


class TestComment:
    @staticmethod
    def test_create_comment():
        comment = Comment(
            id="PRRC_xyz789",
            body="This function is too long",
            author="reviewer",
            created_at="2026-05-12T09:00:00Z",
        )
        assert comment.id == "PRRC_xyz789"
        assert comment.body == "This function is too long"

    @staticmethod
    def test_comment_to_dict():
        comment = Comment(
            id="PRRC_xyz789",
            body="Test comment",
            author="reviewer",
            created_at="2026-05-12T09:00:00Z",
        )
        result = asdict(comment)
        assert result == {
            "id": "PRRC_xyz789",
            "body": "Test comment",
            "author": "reviewer",
            "created_at": "2026-05-12T09:00:00Z",
        }

    @staticmethod
    def test_comment_from_dict():
        data = {
            "id": "PRRC_xyz789",
            "body": "Test comment",
            "author": "reviewer",
            "created_at": "2026-05-12T09:00:00Z",
        }
        comment = Comment.from_dict(data)
        assert comment.id == "PRRC_xyz789"
        assert comment.body == "Test comment"


class TestThread:
    @staticmethod
    def test_create_thread():
        thread = Thread(
            id="PRRT_abc123",
            file="src/foo.py",
            line=42,
            start_line=40,
            resolved=False,
            outdated=False,
            comments=[
                Comment(
                    id="PRRC_xyz789",
                    body="This function is too long",
                    author="reviewer",
                    created_at="2026-05-12T09:00:00Z",
                )
            ],
        )
        assert thread.id == "PRRT_abc123"
        assert thread.file == "src/foo.py"
        assert len(thread.comments) == 1

    @staticmethod
    def test_thread_to_dict():
        thread = Thread(
            id="PRRT_abc123",
            file="src/foo.py",
            line=42,
            start_line=40,
            resolved=False,
            outdated=False,
            comments=[
                Comment(
                    id="PRRC_xyz789",
                    body="Comment",
                    author="reviewer",
                    created_at="2026-05-12T09:00:00Z",
                )
            ],
        )
        result = asdict(thread)
        assert result["id"] == "PRRT_abc123"
        assert result["file"] == "src/foo.py"

    @staticmethod
    def test_thread_from_dict():
        data = {
            "id": "PRRT_abc123",
            "file": "src/foo.py",
            "line": 42,
            "start_line": 40,
            "resolved": False,
            "outdated": False,
            "comments": [
                {
                    "id": "PRRC_xyz789",
                    "body": "Comment",
                    "author": "reviewer",
                    "created_at": "2026-05-12T09:00:00Z",
                }
            ],
        }
        thread = Thread.from_dict(data)
        assert thread.id == "PRRT_abc123"
        assert thread.comments[0].author == "reviewer"


class TestPR:
    @staticmethod
    def test_create_pr():
        pr = PR(
            number=123,
            title="Add feature X",
            url="https://github.com/owner/repo/pull/123",
            base_branch="main",
            head_branch="feature/x",
            state="open",
        )
        assert pr.number == 123
        assert pr.state == "open"

    @staticmethod
    def test_pr_to_dict():
        pr = PR(
            number=123,
            title="Add feature X",
            url="https://github.com/owner/repo/pull/123",
            base_branch="main",
            head_branch="feature/x",
            state="open",
        )
        result = asdict(pr)
        assert result["number"] == 123


class TestMeta:
    @staticmethod
    def test_create_meta():
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc1234ef567",
            pr=PR(
                number=123,
                title="Add feature X",
                url="https://github.com/owner/repo/pull/123",
                base_branch="main",
                head_branch="feature/x",
                state="open",
            ),
        )
        assert meta.rv_version == "0.1.0"
        assert meta.pr.number == 123

    @staticmethod
    def test_meta_to_dict():
        meta = Meta(
            rv_version="0.1.0",
            synced_at="2026-05-13T10:00:00Z",
            synced_at_commit="abc1234ef567",
            pr=PR(
                number=123,
                title="Add feature X",
                url="https://github.com/owner/repo/pull/123",
                base_branch="main",
                head_branch="feature/x",
                state="open",
            ),
        )
        result = asdict(meta)
        assert result["rv_version"] == "0.1.0"
        assert result["pr"]["number"] == 123


class TestState:
    @staticmethod
    def test_create_state():
        state = State(current_thread_id="PRRT_abc123")
        assert state.current_thread_id == "PRRT_abc123"

    @staticmethod
    def test_state_to_dict():
        state = State(current_thread_id="PRRT_abc123")
        result = asdict(state)
        assert result["current_thread_id"] == "PRRT_abc123"

    @staticmethod
    def test_state_from_dict():
        data = {"current_thread_id": "PRRT_abc123"}
        state = State.from_dict(data)
        assert state.current_thread_id == "PRRT_abc123"


class TestThreadFile:
    @staticmethod
    def test_thread_file_path():
        tf = ThreadFile(owner="owner", repo="repo", pr_number=123, thread_id="PRRT_abc")
        expected = "owner/repo/123/threads/PRRT_abc.json"
        assert str(tf) == expected

    @staticmethod
    def test_thread_file_directory():
        tf = ThreadFile(owner="owner", repo="repo", pr_number=123)
        expected = "owner/repo/123/threads"
        assert tf.directory == expected
