from functools import cached_property

from ..domain.ports import VCS, Auth, Forge, Store


class CLIDeps:
    @cached_property
    def store(self) -> Store:
        from ..adapters.peewee.store import PeeweeStore

        return PeeweeStore.open()

    @cached_property
    def runner(self):
        from ..adapters.runner import ProcRunner

        return ProcRunner()

    @cached_property
    def auth(self) -> Auth:
        from ..adapters.auth import AuthProvider

        return AuthProvider(runner=self.runner)

    @cached_property
    def forge(self) -> Forge:
        from ..adapters.github import GitHub

        return GitHub(auth=self.auth)

    @cached_property
    def vcs(self) -> VCS:
        from ..adapters.git import Git

        return Git(runner=self.runner)
