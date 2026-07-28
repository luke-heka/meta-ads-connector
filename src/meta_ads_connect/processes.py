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


def _decode(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw
