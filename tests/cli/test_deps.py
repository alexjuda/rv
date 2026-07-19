from rv.cli._deps import CLIDeps


class TestCLIDeps:
    @staticmethod
    def test_builds_objects():
        deps = CLIDeps()

        _ = deps.forge
        _ = deps.store
        _ = deps.vcs
