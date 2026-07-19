from collections.abc import Collection
from typing import Protocol

from ..models.actions import CollectionStat, ConversationStat
from ..models.github import PRConversation


class EntityObj(Protocol):
    @property
    def id(self) -> str: ...


def collection_stat(
    old: Collection[EntityObj], new: Collection[EntityObj]
) -> CollectionStat:
    old_grouped = {obj.id: obj for obj in old}
    new_grouped = {obj.id: obj for obj in new}

    old_ids = set(old_grouped.keys())
    new_ids = set(new_grouped.keys())

    added_ids = new_ids - old_ids
    deleted_ids = old_ids - new_ids
    both_ids = new_ids & old_ids
    changed_ids = {eid for eid in both_ids if new_grouped[eid] != old_grouped[eid]}

    return CollectionStat(
        n_new=len(added_ids), n_deleted=len(deleted_ids), n_changed=len(changed_ids)
    )


def convo_stat(old: PRConversation, new: PRConversation) -> ConversationStat:
    return ConversationStat(
        threads=collection_stat(old.threads, new.threads),
        pr_comments=collection_stat(old.pr_comments, new.pr_comments),
        reviews=collection_stat(old.reviews, new.reviews),
    )
