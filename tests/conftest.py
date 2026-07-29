"""Test doubles for the two faked boundaries, and nothing else.

These are fakes, not mocks: they behave like the thing they stand in for and
are asserted on through the subcommand's observable results — exit code,
stdout, filesystem. No test asserts that a particular internal function was
called, so a refactor that keeps the subcommands behaving identically cannot
break the suite.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

import pytest

from meta_ads_connect.config import CLI_VERSION, MCP_NAME, MCP_URL, Paths
from meta_ads_connect.context import Context
from meta_ads_connect.graph import GraphError
from meta_ads_connect.processes import CommandNotFound, CommandResult

Responder = Callable[[Sequence[str]], CommandResult]


class FakeCommandRunner:
    """A programmable stand-in for every binary the kit shells out to.

    An unprogrammed command raises :class:`CommandNotFound`, so a test that
    forgets to declare a dependency fails loudly instead of silently reaching
    the real machine.
    """

    def __init__(self) -> None:
        self._path: dict[str, str] = {}
        self._rules: list[tuple[tuple[str, ...], Responder]] = []
        self._pty_rules: list[tuple[tuple[str, ...], Responder]] = []
        self.calls: list[tuple[str, ...]] = []
        self.pty_calls: list[tuple[str, ...]] = []
        #: Environment each call was given, so a test can assert the token was
        #: passed per invocation rather than left somewhere persistent.
        self.environments: list[dict[str, str]] = []

    # --- programming ------------------------------------------------------

    def onPath(self, program: str, location: str | None = None) -> "FakeCommandRunner":
        self._path[program] = location or f"/usr/bin/{program}"
        return self

    def respond(
        self,
        match: Sequence[str],
        *,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
    ) -> "FakeCommandRunner":
        """Answer any command whose argv contains ``match`` in order."""

        def responder(argv: Sequence[str]) -> CommandResult:
            return CommandResult(
                argv=tuple(argv), returncode=returncode, stdout=stdout, stderr=stderr
            )

        self._rules.append((tuple(match), responder))
        return self

    def fails(self, match: Sequence[str], *, stderr: str, returncode: int = 1) -> "FakeCommandRunner":
        return self.respond(match, stderr=stderr, returncode=returncode)

    def sideEffect(self, match: Sequence[str], responder: Responder) -> "FakeCommandRunner":
        self._rules.append((tuple(match), responder))
        return self

    def respondPty(
        self,
        match: Sequence[str],
        *,
        stdout: str = "",
        returncode: int = 0,
    ) -> "FakeCommandRunner":
        """Answer a pty-backed run. A pty has one stream, so there is no stderr."""

        def responder(argv: Sequence[str]) -> CommandResult:
            return CommandResult(argv=tuple(argv), returncode=returncode, stdout=stdout, stderr="")

        self._pty_rules.append((tuple(match), responder))
        return self

    def sideEffectPty(self, match: Sequence[str], responder: Responder) -> "FakeCommandRunner":
        self._pty_rules.append((tuple(match), responder))
        return self

    # --- CommandRunner protocol ------------------------------------------

    def which(self, program: str) -> str | None:
        return self._path.get(program)

    def run(
        self,
        argv: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        argv = list(argv)
        self.calls.append(tuple(argv))
        self.environments.append(dict(env or {}))
        # Most specific rule wins; on a tie the most recently programmed one
        # does, so a test can override a shared setup helper.
        best: tuple[int, Responder] | None = None
        for match, responder in self._rules:
            if _matches(match, argv) and (best is None or len(match) >= best[0]):
                best = (len(match), responder)
        if best is None:
            raise CommandNotFound(argv[0])
        return best[1](argv)

    def runPty(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> CommandResult:
        argv = list(argv)
        self.pty_calls.append(tuple(argv))
        best: tuple[int, Responder] | None = None
        for match, responder in self._pty_rules:
            if _matches(match, argv) and (best is None or len(match) >= best[0]):
                best = (len(match), responder)
        if best is None:
            raise CommandNotFound(argv[0])
        return best[1](argv)

    # --- assertions helpers ----------------------------------------------

    def ranCommandContaining(self, *tokens: str) -> bool:
        return any(_matches(tokens, list(call)) for call in self.calls)


def _matches(match: Sequence[str], argv: Sequence[str]) -> bool:
    """``match`` appears in ``argv`` in order; its first token may be a basename."""
    if not match:
        return False
    remaining = list(argv)
    head, *tail = match
    for index, token in enumerate(remaining):
        if token == head or os.path.basename(token) == head:
            remaining = remaining[index + 1 :]
            break
    else:
        return False
    for token in tail:
        if token in remaining:
            remaining = remaining[remaining.index(token) + 1 :]
        else:
            return False
    return True


class FakeGraphClient:
    """Programmable Graph responses, keyed by the path fragment requested."""

    def __init__(self) -> None:
        self._get: list[tuple[str, Any]] = []
        self._post: list[tuple[str, Any]] = []
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    def onGet(self, path_fragment: str, payload: dict[str, Any] | GraphError) -> "FakeGraphClient":
        self._get.append((path_fragment, payload))
        return self

    def onPost(self, path_fragment: str, payload: dict[str, Any] | GraphError) -> "FakeGraphClient":
        self._post.append((path_fragment, payload))
        return self

    def get(
        self, path: str, *, token: str, params: Mapping[str, str] | None = None
    ) -> dict[str, Any]:
        self.requests.append(("GET", path, dict(params or {})))
        return _resolve(self._get, path)

    def post(
        self, path: str, *, token: str, data: Mapping[str, str] | None = None
    ) -> dict[str, Any]:
        self.requests.append(("POST", path, dict(data or {})))
        return _resolve(self._post, path)

    def pathsRequested(self) -> list[str]:
        return [path for _, path, _ in self.requests]


def _resolve(rules: list[tuple[str, Any]], path: str) -> dict[str, Any]:
    for fragment, payload in rules:
        if fragment in path:
            if isinstance(payload, GraphError):
                raise payload
            assert isinstance(payload, dict)
            return payload
    raise AssertionError(f"FakeGraphClient has no rule for {path!r}")


class Recorder:
    """Captures a stream and lets a test read it back as one string."""

    def __init__(self) -> None:
        self.buffer = io.StringIO()

    def write(self, text: str) -> int:
        return self.buffer.write(text)

    def flush(self) -> None:  # pragma: no cover - stream protocol
        self.buffer.flush()

    @property
    def text(self) -> str:
        return self.buffer.getvalue()


# --- fixtures --------------------------------------------------------------


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    return Paths(root=tmp_path / ".meta-ads")


@pytest.fixture
def runner() -> FakeCommandRunner:
    return FakeCommandRunner()


@pytest.fixture
def graph() -> FakeGraphClient:
    return FakeGraphClient()


@pytest.fixture
def out() -> Recorder:
    return Recorder()


@pytest.fixture
def err() -> Recorder:
    return Recorder()


@pytest.fixture
def ctx(
    paths: Paths,
    runner: FakeCommandRunner,
    graph: FakeGraphClient,
    out: Recorder,
    err: Recorder,
) -> Context:
    return Context(
        paths=paths,
        runner=runner,
        graph=graph,
        out=out,
        err=err,
        platform="darwin",
    )


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the kit's default home at a temp dir, for end-to-end CLI tests."""
    root = tmp_path / "home" / ".meta-ads"
    monkeypatch.setenv("META_ADS_CONNECT_HOME", str(root))
    yield root


# --- shared scenario builders ---------------------------------------------

VALID_TOKEN = "EAAtestsystemusertokenvaluethatislongenoughtolooklikeacredential"

AD_ACCOUNTS_PAYLOAD: dict[str, Any] = {
    "data": [
        {"id": "act_111", "name": "Selr AI", "account_status": 1},
        {"id": "act_222", "name": "Second Account", "account_status": 1},
    ]
}


def installedCli(runner: FakeCommandRunner, paths: Paths, *, version: str = CLI_VERSION) -> None:
    """Put a managed Ads CLI binary on disk and make it answer ``--version``."""
    paths.venv_bin.mkdir(parents=True, exist_ok=True)
    paths.cli_binary.write_text("#!/bin/sh\n")
    paths.cli_binary.chmod(0o755)
    runner.respond(["meta", "--version"], stdout=f"meta-ads {version}")


USER_SCOPE_LINE = "User config (available in all your projects)"
LOCAL_SCOPE_LINE = "Local config (private to you in this project)"


def mcpGetOutput(status: str, *, scope: str = USER_SCOPE_LINE) -> str:
    """What `claude mcp get meta-ads` prints for a registered server."""
    return (
        f"{MCP_NAME}:\n"
        f"  Scope: {scope}\n"
        f"  Status: {status}\n"
        "  Type: http\n"
        f"  URL: {MCP_URL}\n"
    )


def registeredMcp(runner: FakeCommandRunner, *, scope: str = USER_SCOPE_LINE) -> None:
    """Registered, consented, and working — the healthy MCP transport."""
    runner.onPath("claude")
    runner.respond(["claude", "mcp", "get", MCP_NAME], stdout=mcpGetOutput("✓ Connected", scope=scope))


def needsLoginMcp(runner: FakeCommandRunner, *, scope: str = USER_SCOPE_LINE) -> None:
    """Registered but the OAuth flow has never been completed."""
    runner.onPath("claude")
    runner.respond(
        ["claude", "mcp", "get", MCP_NAME],
        stdout=mcpGetOutput("⚠ Needs authentication", scope=scope),
    )


def incompleteMcp(runner: FakeCommandRunner, *, scope: str = USER_SCOPE_LINE) -> None:
    """Consent completed at some point, but the connection does not work —
    the grant may not cover what the kit needs."""
    runner.onPath("claude")
    runner.respond(
        ["claude", "mcp", "get", MCP_NAME],
        stdout=mcpGetOutput("✗ Failed to connect", scope=scope),
    )


def unregisteredMcp(runner: FakeCommandRunner) -> None:
    runner.onPath("claude")
    runner.fails(
        ["claude", "mcp", "get", MCP_NAME],
        stderr=f'No MCP server named "{MCP_NAME}" found.',
    )
    runner.respond(["claude", "mcp", "list"], stdout="No MCP servers configured.")
