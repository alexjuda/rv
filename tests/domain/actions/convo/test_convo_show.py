from datetime import UTC, datetime
from unittest.mock import create_autospec

from rv.domain.actions.convo.show import ShowConvo, ShowConvoUI
from rv.domain.models.github import (
    PR,
    FullPR,
    PRComment,
    PRConversation,
    PRLocator,
    RepoLocator,
    Review,
    Thread,
    ThreadComment,
)
from rv.domain.ports import VCS, Forge, Store


class TestShowConvo:
    @staticmethod
    def test_shows_thread_with_code_context():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        thread = Thread(
            id="thr_1",
            is_resolved=False,
            path="src/main.py",
            line=42,
            commit_sha="abc123",
            comments=[
                ThreadComment(
                    id="c1",
                    body="Fix this",
                    author="alice",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
            ],
        )

        lines = [f"line{i}" for i in range(1, 100)]
        store.get_thread.return_value = thread
        store.get_pr_locator_for_thread.return_value = pr_loc
        vcs.read_file.return_value = "\n".join(lines) + "\n"

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="thr_1", context_lines=2)

        ui.show_thread.assert_called_once()
        call_args = ui.show_thread.call_args
        assert call_args[0][0] is thread
        assert call_args[0][1] == pr_loc
        context = call_args[0][2]
        assert context.path == "src/main.py"
        assert context.commit_sha == "abc123"
        assert context.target_line == 42
        assert context.start_line == 40
        assert context.lines == [f"line{i}" for i in range(40, 45)]

    @staticmethod
    def test_shows_not_found_when_thread_missing():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        store.get_thread.return_value = None
        store.get_pr_comment.return_value = None
        store.get_review.return_value = None

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="missing")

        store.get_thread.assert_called_once_with("missing")
        store.get_pr_comment.assert_called_once_with("missing")
        store.get_review.assert_called_once_with("missing")
        ui.show_thread.assert_not_called()
        ui.show_pr_comment.assert_not_called()
        ui.show_review.assert_not_called()
        ui.show_not_found.assert_called_once_with("missing")

    @staticmethod
    def test_shows_thread_without_code_context_when_read_fails():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        thread = Thread(
            id="thr_1",
            is_resolved=False,
            path="src/main.py",
            line=42,
            commit_sha="abc123",
            comments=[
                ThreadComment(
                    id="c1",
                    body="Fix this",
                    author="alice",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
            ],
        )

        store.get_thread.return_value = thread
        store.get_pr_locator_for_thread.return_value = pr_loc
        vcs.read_file.return_value = None

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="thr_1")

        ui.show_thread.assert_called_once()
        call_args = ui.show_thread.call_args
        assert call_args[0][0] is thread
        assert call_args[0][1] == pr_loc
        assert call_args[0][2] is None

    @staticmethod
    def test_context_truncated_at_file_start():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        thread = Thread(
            id="thr_1",
            is_resolved=False,
            path="x.py",
            line=1,
            commit_sha="abc",
            comments=[
                ThreadComment(
                    id="c1",
                    body="x",
                    author="a",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
            ],
        )
        lines = [f"line{i}" for i in range(1, 100)]
        store.get_thread.return_value = thread
        vcs.read_file.return_value = "\n".join(lines) + "\n"

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="thr_1", context_lines=5)

        context = ui.show_thread.call_args[0][2]
        assert context.start_line == 1
        assert context.lines == [f"line{i}" for i in range(1, 7)]

    @staticmethod
    def test_context_truncated_at_file_end():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        thread = Thread(
            id="thr_1",
            is_resolved=False,
            path="x.py",
            line=99,
            commit_sha="abc",
            comments=[
                ThreadComment(
                    id="c1",
                    body="x",
                    author="a",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
            ],
        )
        lines = [f"line{i}" for i in range(1, 100)]
        store.get_thread.return_value = thread
        vcs.read_file.return_value = "\n".join(lines) + "\n"

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="thr_1", context_lines=5)

        context = ui.show_thread.call_args[0][2]
        assert context.start_line == 94
        assert context.lines == [f"line{i}" for i in range(94, 100)]

    @staticmethod
    def test_shows_pr_comment_when_no_thread():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        comment = PRComment(
            id="pc1",
            author="alice",
            body="Nice PR",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        store.get_thread.return_value = None
        store.get_pr_comment.return_value = comment
        store.get_pr_locator_for_pr_comment.return_value = pr_loc

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="pc1")

        store.get_pr_comment.assert_called_once_with("pc1")
        ui.show_thread.assert_not_called()
        ui.show_pr_comment.assert_called_once_with(comment, pr_loc)

    @staticmethod
    def test_shows_review_when_no_thread_or_comment():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        review = Review(
            id="rv1",
            author="bob",
            body="Looks good",
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            state="approved",
            commit="abc123",
        )
        store.get_thread.return_value = None
        store.get_pr_comment.return_value = None
        store.get_review.return_value = review
        store.get_pr_locator_for_review.return_value = pr_loc

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="rv1")

        store.get_review.assert_called_once_with("rv1")
        ui.show_thread.assert_not_called()
        ui.show_pr_comment.assert_not_called()
        ui.show_review.assert_called_once_with(review, pr_loc)

    @staticmethod
    def test_shows_pr_conversation_for_pr_ref():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        pr_comment = PRComment(
            id="pc1",
            author="alice",
            body="Nice PR",
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        review = Review(
            id="rv1",
            author="bob",
            body="LGTM",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            state="approved",
            commit="abc123",
        )
        full_pr = FullPR(
            pr=PR(
                locator=pr_loc,
                url="",
                title="",
                author="",
                base_branch="",
                head_branch="",
                state="open",
                latest_commit="",
            ),
            convo=PRConversation(
                threads=[],
                pr_comments=[pr_comment],
                reviews=[review],
            ),
        )
        store.get_pr.return_value = full_pr
        vcs.get_origin.return_value = "git@github.com:owner/repo.git"
        forge.parse_repo.return_value = RepoLocator("owner", "repo")

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="#42")

        store.get_pr.assert_called_once()
        args = store.get_pr.call_args[0][0]
        assert args.number == 42
        assert args.repo.owner == "owner"
        assert args.repo.repo == "repo"
        ui.show_pr_conversation.assert_called_once()
        call_args = ui.show_pr_conversation.call_args[0]
        assert call_args[0] == [pr_comment]
        assert call_args[1] == [review]
        assert call_args[2] == pr_loc

    @staticmethod
    def test_pr_ref_not_found_when_pr_missing():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        forge.parse_repo.return_value = RepoLocator("owner", "repo")
        store.get_pr.return_value = None

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="#999")

        ui.show_not_found.assert_called_once_with("#999")
        ui.show_pr_conversation.assert_not_called()

    @staticmethod
    def test_pr_ref_owner_repo_format():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        pr_loc = PRLocator(RepoLocator("other", "proj"), 7)
        full_pr = FullPR(
            pr=PR(
                locator=pr_loc,
                url="",
                title="",
                author="",
                base_branch="",
                head_branch="",
                state="open",
                latest_commit="",
            ),
            convo=PRConversation(threads=[], pr_comments=[], reviews=[]),
        )
        store.get_pr.return_value = full_pr

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="other/proj#7")

        forge.parse_repo.assert_not_called()
        store.get_pr.assert_called_once()
        args = store.get_pr.call_args[0][0]
        assert args.repo.owner == "other"
        assert args.repo.repo == "proj"
        assert args.number == 7
        ui.show_pr_conversation.assert_called_once()

    @staticmethod
    def test_pr_ref_empty_conversation():
        store = create_autospec(Store)
        vcs = create_autospec(VCS)
        forge = create_autospec(Forge)
        ui = create_autospec(ShowConvoUI)

        pr_loc = PRLocator(RepoLocator("owner", "repo"), 42)
        full_pr = FullPR(
            pr=PR(
                locator=pr_loc,
                url="",
                title="",
                author="",
                base_branch="",
                head_branch="",
                state="open",
                latest_commit="",
            ),
            convo=PRConversation(threads=[], pr_comments=[], reviews=[]),
        )
        forge.parse_repo.return_value = RepoLocator("owner", "repo")
        store.get_pr.return_value = full_pr

        action = ShowConvo(store=store, vcs=vcs, forge=forge, ui=ui)
        action.exec(id="#42")

        ui.show_pr_conversation.assert_called_once()
        call_args = ui.show_pr_conversation.call_args[0]
        assert call_args[0] == []
        assert call_args[1] == []
        assert call_args[2] == pr_loc
