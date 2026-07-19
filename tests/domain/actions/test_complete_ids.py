from datetime import UTC, datetime
from unittest.mock import create_autospec

from rv.domain.actions.complete_ids import CompleteIDs, CompleteIDsUI
from rv.domain.models.github import PRComment, Review
from rv.domain.ports import Store


class TestCompleteIDs:
    @staticmethod
    def test_includes_pr_comments_and_reviews():
        store = create_autospec(Store)
        ui = create_autospec(CompleteIDsUI)

        store.get_threads_matching.return_value = []
        store.get_thread_comments_matching.return_value = []
        store.get_pr_comments_matching.return_value = [
            PRComment(
                id="pc1",
                author="alice",
                body="Nice PR",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ]
        store.get_reviews_matching.return_value = [
            Review(
                id="rv1",
                author="bob",
                body="LGTM",
                created_at=datetime(2026, 1, 2, tzinfo=UTC),
                state="approved",
                commit="abc123",
            ),
        ]

        ui.format_pr_comment.return_value = ("pc1", "pr comment")
        ui.format_review.return_value = ("rv1", "review: approved")

        action = CompleteIDs(store=store, ui=ui)
        result = action.exec(id_prefix="")

        assert result == [("pc1", "pr comment"), ("rv1", "review: approved")]
        ui.format_pr_comment.assert_called_once()
        ui.format_review.assert_called_once()
