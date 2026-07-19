from ...domain.models.actions import StatusSummary


class TextStatusUI:
    def show_summary(self, summary: StatusSummary):
        print(f"{summary.stored_n_prs} PRs stored locally.")

        self._print_if_positive(summary.stale_n_prs, "\n{} stale PRs -> `rv pull`")

        if summary.pending_n_prs > 0:
            print()
            print("Pending changes:")

            self._print_if_positive(
                summary.pending_comments_stat.n_new, "* {} new comments"
            )
            self._print_if_positive(
                summary.pending_comments_stat.n_changed, "* {} edited comments"
            )
            self._print_if_positive(
                summary.pending_comments_stat.n_deleted, "* {} deleted comments"
            )
            self._print_if_positive(
                summary.pending_threads_stat.n_new, "* {} new threads"
            )
            self._print_if_positive(
                summary.pending_threads_stat.n_deleted, "* {} deleted threads"
            )
            self._print_if_positive(
                summary.pending_threads_stat.n_resolved, "* {} resolved threads"
            )
            print(f"...across {summary.pending_n_prs} PRs. -> `rv push`")
            print()

        if (
            summary.unresolved_n_prs > 0
            or summary.unreviewed_n_prs > 0
            or summary.reviewed_n_prs > 0
        ):
            print()
            print("Work:")
            self._print_if_positive(
                summary.unresolved_n_prs,
                f"* {summary.unresolved_n_threads} "
                "unresolved threads across {} PRs -> `rv thread list`, `rv thread reply`, `rv thread resolve`",
            )

            self._print_if_positive(
                summary.unreviewed_n_prs,
                "* {} PRs waiting for review -> `rv review add`",
            )
            self._print_if_positive(
                summary.reviewed_n_prs,
                "* {} reviewed PRs waiting for action -> `rv pr checkout`",
            )

    @staticmethod
    def _print_if_positive(value: int, format_str: str):
        if value > 0:
            print(format_str.format(value))
