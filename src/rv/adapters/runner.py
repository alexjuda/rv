import subprocess


class CmdError(Exception):
    def __init__(self, cmd: list[str], stdout: bytes, stderr: bytes, retcode: int):
        super().__init__(cmd, stdout, stderr, retcode)


class ProcRunner:
    def stdout(self, cmd: list[str]) -> list[str]:
        proc = subprocess.run(cmd, capture_output=True)  # noqa: PLW1510
        if proc.returncode != 0:
            raise CmdError(
                cmd=cmd,
                stdout=proc.stdout,
                stderr=proc.stderr,
                retcode=proc.returncode,
            )

        return proc.stdout.decode().splitlines()

    def merged_outputs(self, cmd: list[str]) -> list[str]:
        proc = subprocess.run(cmd, capture_output=True)  # noqa: PLW1510
        if proc.returncode != 0:
            raise CmdError(
                cmd=cmd,
                stdout=proc.stdout,
                stderr=proc.stderr,
                retcode=proc.returncode,
            )

        stdout_lines = proc.stdout.decode().splitlines()
        stderr_lines = proc.stderr.decode().splitlines()

        return stdout_lines + stderr_lines
