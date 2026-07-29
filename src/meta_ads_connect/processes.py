"""Subprocess boundary.

One of exactly two boundaries the test suite fakes. Every external binary the
kit shells out to — ``python``, ``pip``, ``meta``, ``claude`` — goes through
:class:`CommandRunner`, so tests can present a binary that is absent, present at
the wrong version, present and healthy, or failing, without touching the machine.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def output(self) -> str:
        """Both streams, for callers matching on a message that could be on either."""
        return f"{self.stdout}\n{self.stderr}"


class CommandNotFound(Exception):
    """Raised when the binary itself is missing, as opposed to failing."""

    def __init__(self, program: str) -> None:
        super().__init__(f"{program} not found")
        self.program = program


class CommandRunner(Protocol):
    def which(self, program: str) -> str | None:
        """Absolute path to ``program`` on PATH, or None."""

    def run(
        self,
        argv: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        """Run to completion. Never raises on a non-zero exit code.

        Raises :class:`CommandNotFound` when the binary does not exist, and
        returns a result with a non-zero code for every other failure —
        including a timeout, so callers have one shape to handle.
        """

    def runPty(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        """Run under a pseudo-terminal, for commands that refuse a plain pipe.

        ``claude mcp login`` requires a controlling terminal: from an ordinary
        subprocess it exits with "stdin isn't a terminal". Under a pty it
        completes on its own — the localhost OAuth callback does the work and
        nothing needs typing. Same error contract as :meth:`run`; the two
        output streams arrive interleaved on ``stdout`` because a pty has only
        one. POSIX only — callers gate on platform before reaching for this.
        """


class RealCommandRunner:
    """The production implementation. Thin on purpose: it holds no policy."""

    def which(self, program: str) -> str | None:
        return shutil.which(program)

    def run(
        self,
        argv: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        argv = list(argv)
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise CommandNotFound(argv[0]) from exc
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                argv=tuple(argv),
                returncode=124,
                stdout=_decode(exc.stdout),
                stderr=f"timed out after {timeout}s",
            )
        return CommandResult(
            argv=tuple(argv),
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

    def runPty(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        import os
        import pty
        import select
        import time

        argv = list(argv)
        master, slave = pty.openpty()
        try:
            proc = subprocess.Popen(
                argv,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
            )
        except FileNotFoundError as exc:
            os.close(master)
            os.close(slave)
            raise CommandNotFound(argv[0]) from exc
        os.close(slave)

        chunks: list[bytes] = []
        deadline = time.monotonic() + timeout if timeout is not None else None
        timed_out = False
        while True:
            if deadline is not None and time.monotonic() > deadline:
                proc.kill()
                timed_out = True
                break
            ready, _, _ = select.select([master], [], [], 0.5)
            if ready:
                try:
                    data = os.read(master, 4096)
                except OSError:
                    # The child closed its end; on Linux this raises EIO.
                    break
                if not data:
                    break
                chunks.append(data)
            elif proc.poll() is not None:
                break
        os.close(master)
        returncode = proc.wait()
        output = b"".join(chunks).decode("utf-8", errors="replace")
        if timed_out:
            return CommandResult(
                argv=tuple(argv),
                returncode=124,
                stdout=output,
                stderr=f"timed out after {timeout}s",
            )
        return CommandResult(argv=tuple(argv), returncode=returncode, stdout=output, stderr="")


def _decode(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw
