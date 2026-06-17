from ...domain.models.github import Thread, ThreadComment


class TextShowUI:
    def show_thread(self, thread: Thread) -> None:
        print(f"Thread #{thread.id}, {len(thread.comments)} comments")
        for comment in thread.comments:
            print()
            self.show_thread_comment(comment)

    def show_thread_comment(self, thread_comment: ThreadComment) -> None:
        print(thread_comment.body)
        print(
            f" ~@{thread_comment.author}, {thread_comment.created_at.astimezone()}, #{thread_comment.id}"
        )


class TextCompleteIDsUI:
    def format_thread(self, thread: Thread) -> tuple[str, str]:
        th = thread
        return (
            th.id,
            f"Thread by @{th.comments[0].author}, {len(th.comments) - 1} replies",
        )

    def format_thread_comment(self, thread_comment: ThreadComment) -> tuple[str, str]:
        comm = thread_comment
        return (comm.id, f"Comment by @{comm.author}, {comm.body[:20]}...")
