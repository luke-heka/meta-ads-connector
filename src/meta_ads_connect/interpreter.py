"""Resolving a Python the Ads CLI actually has wheels for.

The CLI is mypyc-compiled and publishes cp312/cp313 wheels with no sdist. On
any other interpreter ``pip install`` fails outright — this was hit twice
during research, so it is a handled case rather than a hypothetical one. The
kit picks the interpreter itself instead of assuming the ambient one.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

from .config import SUPPORTED_PYTHONS
from .processes import CommandNotFound, CommandRunner

_VERSION_OUTPUT = re.compile(r"Python\s+(\d+)\.(\d+)(?:\.(\d+))?")


@dataclass(frozen=True)
class FoundInterpreter:
    path: str
    version: tuple[int, int]

    @property
    def label(self) -> str:
        return f"Python {self.version[0]}.{self.version[1]}"

    @property
    def supported(self) -> bool:
        return self.version in SUPPORTED_PYTHONS


@dataclass(frozen=True)
class Resolution:
    """What the search found. ``chosen`` is None when nothing was suitable."""

    chosen: FoundInterpreter | None
    considered: tuple[FoundInterpreter, ...]

    def explain(self) -> str:
        """Why this failed, naming what was actually on the machine.

        A business owner cannot act on "no suitable Python found"; they can act
        on "you have 3.14, the Ads CLI needs 3.13".
        """
        if self.chosen is not None:
            return f"Using {self.chosen.label} at {self.chosen.path}."

        wanted = " or ".join(f"{major}.{minor}" for major, minor in SUPPORTED_PYTHONS)
        if not self.considered:
            return (
                f"No Python was found on this machine. The Meta Ads CLI needs Python {wanted}. "
                "Install one from python.org, or with Homebrew: brew install python@3.13"
            )
        found = ", ".join(sorted({item.label for item in self.considered}))
        return (
            f"Found {found}, but the Meta Ads CLI only publishes builds for Python {wanted}. "
            "It is a compiled package with no source fallback, so a newer Python cannot be "
            "made to work. Install one alongside what you have — nothing you already use "
            "will change: brew install python@3.13"
        )


def resolveInterpreter(runner: CommandRunner, *, recorded: str | None = None) -> Resolution:
    """Find the best interpreter for the Ads CLI, preferring 3.13 then 3.12.

    Candidates are the version-suffixed executables on PATH, plus the
    interpreter running this code, which covers a virtualenv or a pyenv shim
    that does not publish a suffixed name.

    ``recorded`` is what a previous run settled on. It is re-checked rather
    than trusted — an interpreter can be uninstalled or upgraded out of support
    between runs — but when it still holds up, it wins and the search is
    skipped, which is the point of recording it.
    """
    considered: list[FoundInterpreter] = []
    seen_paths: set[str] = set()

    if recorded:
        remembered = _inspect(runner, recorded)
        if remembered is not None and remembered.supported:
            return Resolution(chosen=remembered, considered=(remembered,))

    for major, minor in SUPPORTED_PYTHONS:
        program = f"python{major}.{minor}"
        located = runner.which(program)
        if located is None or located in seen_paths:
            continue
        seen_paths.add(located)
        found = _inspect(runner, located)
        if found is not None:
            considered.append(found)

    for program in ("python3", "python"):
        located = runner.which(program)
        if located is None or located in seen_paths:
            continue
        seen_paths.add(located)
        found = _inspect(runner, located)
        if found is not None:
            considered.append(found)

    running = (sys.version_info.major, sys.version_info.minor)
    if sys.executable and sys.executable not in seen_paths:
        considered.append(FoundInterpreter(path=sys.executable, version=running))

    for wanted in SUPPORTED_PYTHONS:
        for candidate in considered:
            if candidate.version == wanted:
                return Resolution(chosen=candidate, considered=tuple(considered))

    return Resolution(chosen=None, considered=tuple(considered))


def _inspect(runner: CommandRunner, path: str) -> FoundInterpreter | None:
    try:
        result = runner.run([path, "--version"], timeout=20)
    except CommandNotFound:
        return None
    if not result.ok:
        return None
    match = _VERSION_OUTPUT.search(result.output)
    if match is None:
        return None
    return FoundInterpreter(path=path, version=(int(match.group(1)), int(match.group(2))))
