from ...domain.models.actions import PRLocator, PullSummary


class TextPullUI:
    def fetching_heads_up(self, pr_loc: PRLocator):
        print(f"Fetching {self._format_pr(pr_loc)}")

    @staticmethod
    def _format_pr(pr: PRLocator) -> str:
        return f"{pr.repo.owner}/{pr.repo.repo}#{pr.number}"

    def confirm(self, summary: PullSummary) -> bool:
        self.ack_summary(summary)

        resp = input("Confirm pull? [Y/n] ")
        return not resp or resp.lower() in {"y", "yes"}

    def ack_confirmation(self, saved: bool):
        if saved:
            print("Local store updated.")
        else:
            print("Skipped.")

    def ack_summary(self, summary: PullSummary):
        print(f"Fetched {self._format_pr(summary.pr_loc)}")

        something = False

        for name, stat in [
            ("inline threads", summary.stat.threads),
            ("PR comments", summary.stat.pr_comments),
            ("PR reviews", summary.stat.reviews),
        ]:
            if stat.n_new > 0:
                print(f"  {stat.n_new} new {name}")
                something = True
            if stat.n_deleted > 0:
                print(f"  {stat.n_deleted} deleted {name}")
                something = True
            if stat.n_changed > 0:
                print(f"  {stat.n_changed} edited {name}")
                something = True

        if not something:
            print("  No changes")
