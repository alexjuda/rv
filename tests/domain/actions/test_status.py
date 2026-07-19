from unittest.mock import create_autospec

from pytest import fixture

from rv.domain.actions.status import Status, StatusUI
from rv.domain.ports import Store

# --- mock fixtures ---


@fixture
def store():
    return create_autospec(Store)


@fixture
def ui():
    return create_autospec(StatusUI)


@fixture
def action(store, ui):
    return Status(store=store, ui=ui)


# --- data fixtures ---


# --- test cases ---


class TestShow:
    # --- happy path ---
    @staticmethod
    def test_one_pr(ui, store, action: Status):
        action.exec()
