from typing import Protocol

from ..exceptions import PRNotFoundError
from ..models.actions import CollectionStat, ConversationStat, PullSummary
from ..models.github import FullPR, PRLocator
from ..ports import VCS, Forge, Store
from ._resolve import resolve_pr_loc
from ._stat import convo_stat


class PullUI(Protocol):
    def fetching_heads_up(self, pr_loc: PRLocator):
        """
        Notify that we're fetching a PR.
        """
        ...

    def confirm(self, summary: PullSummary) -> bool:
        """
        Ask the user if it's okay to perform the pull.
        """
        ...

    def ack_confirmation(self, saved: bool):
        """
        Tell the user that the PR was stored or was skipped.
        """
        ...

    def ack_summary(self, summary: PullSummary):
        """
        Tell the user that the PR was stored. And show summary.
        """
        ...


class Pull:
    def __init__(self, store: Store, forge: Forge, vcs: VCS, ui: PullUI):
        self._store = store
        self._forge = forge
        self._vcs = vcs
        self._ui = ui

    async def exec(self, pr_arg: int | PRLocator | None) -> None:
        pr_loc = await resolve_pr_loc(pr_arg, vcs=self._vcs, forge=self._forge)

        self._ui.fetching_heads_up(pr_loc)
        if not (pulled_pr := await self._forge.get_pr(pr_loc)):
            raise PRNotFoundError(pr_loc)

        if old_pr := self._store.get_pr(pr_loc):
            stat = convo_stat(old=old_pr.convo, new=pulled_pr.convo)
        else:
            stat = self._all_new_pr_stat(pulled_pr)

        is_destructive = any(
            coll.n_changed > 0 or coll.n_deleted > 0
            for coll in [stat.threads, stat.pr_comments, stat.reviews]
        )

        summary = PullSummary(stat=stat, pr_loc=pr_loc)
        if is_destructive:
            accepted = self._ui.confirm(summary)
            self._ui.ack_confirmation(accepted)
            if not accepted:
                return
        else:
            self._ui.ack_summary(summary)

        self._store.store_pr(pulled_pr)

    @classmethod
    def _all_new_pr_stat(cls, pr: FullPR) -> ConversationStat:
        return ConversationStat(
            threads=cls._all_new_coll_stat(pr.convo.threads),
            pr_comments=cls._all_new_coll_stat(pr.convo.pr_comments),
            reviews=cls._all_new_coll_stat(pr.convo.reviews),
        )

    @staticmethod
    def _all_new_coll_stat(coll: list) -> CollectionStat:
        return CollectionStat(
            n_new=len(coll),
            n_deleted=0,
            n_changed=0,
        )
