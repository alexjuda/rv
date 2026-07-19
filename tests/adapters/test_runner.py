from pytest import fixture, raises

from rv.adapters.runner import CmdError, ProcRunner


@fixture
def runner():
    return ProcRunner()


class TestProcRunner:
    class TestStdout:
        @staticmethod
        def test_success(runner: ProcRunner):
            outputs = runner.stdout(["echo", "foo"])
            assert outputs == ["foo"]

        @staticmethod
        def test_failure(runner: ProcRunner):
            with raises(CmdError):
                _ = runner.stdout(["false"])

    class TestMergedOutputs:
        @staticmethod
        def test_stdout(runner: ProcRunner):
            outputs = runner.merged_outputs(["echo", "foo"])
            assert outputs == ["foo"]

        @staticmethod
        def test_stderr(runner: ProcRunner):
            outputs = runner.merged_outputs(
                ["python3", "-c", "import sys; print('foo', file=sys.stderr)"]
            )
            assert outputs == ["foo"]

        @staticmethod
        def test_both(runner: ProcRunner):
            outputs = runner.merged_outputs(
                [
                    "python3",
                    "-c",
                    """
import sys
print("msg1")
print("msg2", file=sys.stderr)
print("msg3")
print("msg4", file=sys.stderr)
                    """,
                ]
            )
            assert outputs == ["msg1", "msg3", "msg2", "msg4"]
