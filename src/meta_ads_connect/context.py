"""What every subcommand is handed.

Collecting the four replaceable things — filesystem root, subprocess runner,
Graph client, output streams — into one object is what lets the test suite
drive real subcommands end to end without touching the machine or the network.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Protocol

from .config import Paths, defaultPaths
from .graph import GraphClient, HttpGraphClient
from .processes import CommandRunner, RealCommandRunner
from .tokens import redact


class Writer(Protocol):
    """All the kit ever needs of an output stream.

    Narrower than ``TextIO`` on purpose: declaring the whole file protocol
    would force anything standing in for a stream to implement thirty methods
    the kit never calls.
    """

    def write(self, text: str, /) -> int: ...


@dataclass
class Context:
    paths: Paths = field(default_factory=defaultPaths)
    runner: CommandRunner = field(default_factory=RealCommandRunner)
    graph: GraphClient = field(default_factory=HttpGraphClient)
    out: Writer = field(default_factory=lambda: sys.stdout)
    err: Writer = field(default_factory=lambda: sys.stderr)
    platform: str = field(default_factory=lambda: sys.platform)

    #: Set once a token has been read, so every subsequent write is scrubbed
    #: of it. Assigned by the subcommands, never by callers.
    secret: str | None = None

    @property
    def is_windows(self) -> bool:
        """Native Windows. WSL reports as ``linux`` and is fully supported."""
        return self.platform.startswith("win")

    def say(self, message: str = "") -> None:
        self.out.write(redact(message, token=self.secret) + "\n")

    def warn(self, message: str = "") -> None:
        self.err.write(redact(message, token=self.secret) + "\n")
