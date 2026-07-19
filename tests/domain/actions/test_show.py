from unittest.mock import create_autospec

from pytest import fixture, raises

from rv.domain.actions.show import Show, ShowUI
from rv.domain.exceptions import IDNotFoundError
from rv.domain.models.github import Thread, ThreadComment
from rv.domain.ports import Store

# --- mock fixtures ---


@fixture
def store():
    return create_autospec(Store)


@fixture
def ui():
    return create_autospec(ShowUI)


@fixture
def action(store, ui):
    return Show(store=store, ui=ui)


# --- data fixtures ---


# --- test cases ---


class TestShow:
    # --- happy path ---
    @staticmethod
    async def test_with_thread_id(ui, store, action: Show, sample_thread: Thread):
        store.get_thread.return_value = sample_thread
        id = sample_thread.id

        await action.exec(id=id)

        ui.show_thread.assert_called()
        thread: Thread = ui.show_thread.call_args.args[0]

        assert thread.id == id
        assert len(thread.comments) == len(sample_thread.comments)

    @staticmethod
    async def test_with_thread_comment_id(
        ui, store, action: Show, sample_thread_comment: ThreadComment
    ):
        store.get_thread.return_value = None
        store.get_thread_comment.return_value = sample_thread_comment
        id = sample_thread_comment.id

        await action.exec(id=id)

        ui.show_thread_comment.assert_called()
        comment: ThreadComment = ui.show_thread_comment.call_args.args[0]

        assert comment.id == id
        assert comment.author == sample_thread_comment.author
        assert comment.body == sample_thread_comment.body

    # --- errors ---

    @staticmethod
    async def test_with_invalid_id(store, action: Show):
        store.get_thread.return_value = None
        store.get_thread_comment.return_value = None
        id = "invalid"

        with raises(IDNotFoundError):
            await action.exec(id=id)
