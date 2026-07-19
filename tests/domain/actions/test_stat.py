from dataclasses import dataclass

from rv.domain.actions._stat import collection_stat, convo_stat
from rv.domain.models.github import PRConversation


@dataclass
class SimpleObj:
    id: str
    name: str | None = None


class TestCollectionStat:
    @staticmethod
    def test_empty_empty():
        old = new = []

        stat = collection_stat(old, new)

        assert stat.n_new == 0
        assert stat.n_deleted == 0
        assert stat.n_changed == 0

    @staticmethod
    def test_some_new():
        old = [SimpleObj(id="1")]
        new = [SimpleObj(id="1"), SimpleObj(id="2")]

        stat = collection_stat(old, new)

        assert stat.n_new == 1
        assert stat.n_deleted == 0
        assert stat.n_changed == 0

    @staticmethod
    def test_some_deleted():
        old = [SimpleObj(id="1"), SimpleObj(id="2")]
        new = [SimpleObj(id="1")]

        stat = collection_stat(old, new)

        assert stat.n_new == 0
        assert stat.n_deleted == 1
        assert stat.n_changed == 0

    @staticmethod
    def test_some_changed():
        old = [SimpleObj(id="1"), SimpleObj(id="2", name="foo")]
        new = [SimpleObj(id="1"), SimpleObj(id="2", name="bar")]

        stat = collection_stat(old, new)

        assert stat.n_new == 0
        assert stat.n_deleted == 0
        assert stat.n_changed == 1

    @staticmethod
    def none_matching():
        old = [SimpleObj(id="1")]
        new = [SimpleObj(id="2")]

        stat = collection_stat(old, new)

        assert stat.n_new == 1
        assert stat.n_deleted == 1
        assert stat.n_changed == 0


class TestConvoStat:
    @staticmethod
    def test_empty_empty():
        old = new = PRConversation([], [], [])

        stat = convo_stat(old, new)

        assert stat.threads.n_new == 0
        assert stat.threads.n_deleted == 0
        assert stat.threads.n_changed == 0

        assert stat.pr_comments.n_new == 0
        assert stat.pr_comments.n_deleted == 0
        assert stat.pr_comments.n_changed == 0

        assert stat.reviews.n_new == 0
        assert stat.reviews.n_deleted == 0
        assert stat.reviews.n_changed == 0

    @staticmethod
    def test_empty():
        old = new = PRConversation([], [], [])

        stat = convo_stat(old, new)

        assert stat.threads.n_new == 0
        assert stat.threads.n_deleted == 0
        assert stat.threads.n_changed == 0

        assert stat.pr_comments.n_new == 0
        assert stat.pr_comments.n_deleted == 0
        assert stat.pr_comments.n_changed == 0

        assert stat.reviews.n_new == 0
        assert stat.reviews.n_deleted == 0
        assert stat.reviews.n_changed == 0
